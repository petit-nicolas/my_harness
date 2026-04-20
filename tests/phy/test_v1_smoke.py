"""V1 冒烟测试（V1.6）— 端到端串通 Wiki 四工具 + Mineru 纯函数 + mode 隔离。

设计原则
--------
- **不打 MinerU 真 API**：成本 / 速度 / 网络依赖；真 API 链路已在 V1.4 单独验证过。
  本测试只覆盖 mineru.py 内的纯函数（页数估算、图片路径重写、CLI 入参解析），
  确保未来 refactor 不破坏这些已通过验证的核心逻辑。
- **不污染真实 wiki**：通过 monkeypatch 把 `wiki.WIKI_ROOT` 临时切到 tempdir；
  每个测试用例独立 setUp/tearDown，互不影响。
- **零外部依赖**：只用 stdlib unittest，不引入 pytest（与 wiki.py 同一原则）。
- **直接可跑**：

    python tests/phy/test_v1_smoke.py

  也可走 unittest discover：

    python -m unittest tests.phy.test_v1_smoke -v

覆盖矩阵
--------
A. Mineru 纯函数（4 用例 × 多 case）
B. Wiki 端到端流水线（write → read → search → index → rebuild → 二次幂等）
C. mode 隔离（runner 严格只读，builder 才有 write/index）
D. 边界与回归（断裂链接、image 路径双前缀回归）
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

# 让 src.* 可导入：tests/phy/test_v1_smoke.py → 上溯两级到仓库根
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.phy import wiki  # noqa: E402
from src.phy.tools import mineru  # noqa: E402


# ---------------------------------------------------------------------------
# A. Mineru 纯函数
# ---------------------------------------------------------------------------

class MineruPureFnTests(unittest.TestCase):
    """mineru.py 的非网络部分。"""

    # --- _estimate_page_count ---

    def test_estimate_basic_range(self):
        self.assertEqual(mineru._estimate_page_count("45-78"), 34)

    def test_estimate_single_page(self):
        self.assertEqual(mineru._estimate_page_count("5"), 1)

    def test_estimate_mixed(self):
        # "2,4-6,10" → 1 + 3 + 1 = 5
        self.assertEqual(mineru._estimate_page_count("2,4-6,10"), 5)

    def test_estimate_invalid_returns_none(self):
        self.assertIsNone(mineru._estimate_page_count("foo"))
        self.assertIsNone(mineru._estimate_page_count("10-5"))  # 倒序
        self.assertIsNone(mineru._estimate_page_count(""))

    def test_estimate_soft_limit_constant(self):
        # 软上限不能被悄悄改小，否则用户已习惯的 30 页警告会失灵
        self.assertEqual(mineru.PAGE_RANGE_SOFT_LIMIT, 30)

    # --- _rewrite_image_paths ---

    def test_rewrite_md_image(self):
        out = mineru._rewrite_image_paths("![alt](images/d2.png)", "ch3-images")
        self.assertEqual(out, "![alt](./ch3-images/d2.png)")

    def test_rewrite_html_image(self):
        out = mineru._rewrite_image_paths('<img src="images/d2.png" />', "ch3-images")
        self.assertIn('src="./ch3-images/d2.png"', out)

    def test_rewrite_no_double_prefix_regression(self):
        """V1.3 修过的回归：HTML 图片路径不能出现 ././"""
        text = (
            "![](images/a.png)\n"
            "<img src='images/b.png' />\n"
            '<img src="images/c.png" />'
        )
        out = mineru._rewrite_image_paths(text, "x-images")
        self.assertNotIn("././", out)
        self.assertIn("./x-images/a.png", out)
        self.assertIn("./x-images/b.png", out)
        self.assertIn("./x-images/c.png", out)

    def test_rewrite_preserves_non_image_lines(self):
        text = "这是正文\n\n![插图](images/x.png)\n\n## 第二节"
        out = mineru._rewrite_image_paths(text, "ch3-images")
        self.assertIn("这是正文", out)
        self.assertIn("## 第二节", out)
        self.assertIn("![插图](./ch3-images/x.png)", out)

    # --- CLI parser ---

    def test_cli_parser_file_subcommand(self):
        parser = mineru._build_parser()
        args = parser.parse_args(
            ["file", "x.pdf", "--output", "out", "--page-ranges", "1-5"]
        )
        self.assertEqual(args.cmd, "file")
        self.assertEqual(args.path, "x.pdf")
        self.assertEqual(args.output, "out")
        self.assertEqual(args.page_ranges, "1-5")
        # 默认 vlm + 公式开 + 表开
        self.assertEqual(args.model, mineru.DEFAULT_MODEL)
        self.assertFalse(args.no_formula)
        self.assertFalse(args.no_table)

    def test_cli_parser_url_subcommand(self):
        parser = mineru._build_parser()
        args = parser.parse_args(
            ["url", "https://x/y.pdf", "--output", "out", "--page-ranges", "1-3"]
        )
        self.assertEqual(args.cmd, "url")
        self.assertEqual(args.file_url, "https://x/y.pdf")

    def test_cli_parser_unknown_subcommand_fails(self):
        parser = mineru._build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["batch", "x.pdf"])  # 不支持的子命令


# ---------------------------------------------------------------------------
# B & C. Wiki 端到端 + mode 隔离
# ---------------------------------------------------------------------------

INDEX_SKELETON = (
    "---\nid: index\ntitle: idx\nlevel: meta\n"
    "created: 2026-04-19\nupdated: 2026-04-19\n---\n\n"
    "# Wiki 主索引\n\n"
    "## 按学科\n\n"
    "## 按教材\n"
)

OVERVIEW_SKELETON = (
    "---\nid: overview\ntitle: ov\nlevel: meta\n"
    "created: 2026-04-19\nupdated: 2026-04-19\n---\n\n"
    "# 覆盖度概览\n\n"
    "## 知识库统计\n\n"
    "（占位）\n"
)


def _isolated_wiki_root() -> Path:
    """建一个临时 wiki 根 + 写入最小 index/overview 骨架，便于 rebuild 流程跑通。"""
    tmp = Path(tempfile.mkdtemp(prefix="phy_v16_wiki_"))
    (tmp / "index.md").write_text(INDEX_SKELETON, encoding="utf-8")
    (tmp / "overview.md").write_text(OVERVIEW_SKELETON, encoding="utf-8")
    (tmp / "sources").mkdir(parents=True, exist_ok=True)
    (tmp / "mechanics").mkdir(parents=True, exist_ok=True)
    return tmp


class WikiEndToEndTests(unittest.TestCase):
    """端到端：write → read → search → index → rebuild → 二次幂等。"""

    def setUp(self) -> None:
        self.tmp = _isolated_wiki_root()
        self._orig_root = wiki.WIKI_ROOT
        wiki.WIKI_ROOT = self.tmp

    def tearDown(self) -> None:
        wiki.WIKI_ROOT = self._orig_root
        shutil.rmtree(self.tmp, ignore_errors=True)

    # -- B1. 创建一个 sources 摘要页（模拟 ingest 步骤 5） --

    def test_b1_write_sources_summary_page(self):
        page_id = "sources/pep-required-1-ch3"
        content = (
            "---\n"
            "id: sources/pep-required-1-ch3\n"
            "title: 人教必修一·第3章 相互作用·力\n"
            "level: meta\n"
            "source_file: res/phy/raw/pep/required-1/full.pdf\n"
            "page_ranges: 45-78\n"
            "---\n\n"
            "## 章节摘要\n\n"
            "本章覆盖力的合成与分解、共点力平衡。\n\n"
            "相关概念：[[mechanics/force-composition]]\n"
        )
        report = wiki.wiki_write(page_id, content)
        self.assertIn("已创建", report)
        self.assertTrue((self.tmp / "sources/pep-required-1-ch3.md").exists())

    # -- B2. 创建一个力学概念页 + 反链 --

    def test_b2_write_mechanics_concept_page(self):
        # 先建摘要页（被反链的目标）
        wiki.wiki_write(
            "sources/pep-required-1-ch3",
            "---\nid: sources/pep-required-1-ch3\ntitle: src\nlevel: meta\n---\n\n# x\n",
        )
        page_id = "mechanics/force-composition"
        content = (
            "---\n"
            "title: 力的合成与分解\n"
            "level: basic\n"
            "sources: [[sources/pep-required-1-ch3]]\n"
            "---\n\n"
            "## 定义\n\n"
            "若一个力的作用效果与几个力的作用效果相同，前者称为后者的合力。\n\n"
            "**前置**：[[sources/pep-required-1-ch3]]\n"
        )
        report = wiki.wiki_write(page_id, content)
        self.assertIn("已创建", report)

        # 自动注入 / auto-fix
        self.assertIn("created 未填", report)
        self.assertIn("updated 自动刷新", report)

    # -- B3. 读回，frontmatter 与正文齐全 --

    def test_b3_read_after_write_roundtrip(self):
        page_id = "mechanics/newton-second-law"
        wiki.wiki_write(
            page_id,
            "---\ntitle: 牛顿第二定律\nlevel: basic\n---\n\n## 表达式\n\nF = ma\n",
        )
        text = wiki.wiki_read(page_id)
        self.assertNotIn("错误", text)
        self.assertIn("title: 牛顿第二定律", text)
        self.assertIn("F = ma", text)
        # auto-injected fields 应该出现
        self.assertIn("created:", text)
        self.assertIn("updated:", text)
        self.assertIn("subject: mechanics", text)  # 推断的

    # -- B4. 搜索覆盖 5 种 scope --

    def test_b4_search_5_scopes(self):
        wiki.wiki_write(
            "mechanics/newton-second-law",
            "---\ntitle: 牛顿第二定律\nlevel: basic\n---\n\nF = ma 是核心 → [[mechanics/force-composition]]\n",
        )
        wiki.wiki_write(
            "mechanics/force-composition",
            "---\ntitle: 力的合成\nlevel: basic\n---\n\n平行四边形定则\n",
        )

        # all
        out = wiki.wiki_search("F = ma")
        self.assertIn("mechanics/newton-second-law", out)
        # title
        out = wiki.wiki_search("力的合成", scope="title")
        self.assertIn("mechanics/force-composition", out)
        # body
        out = wiki.wiki_search("平行四边形", scope="body")
        self.assertIn("mechanics/force-composition", out)
        # wikilink（反向链接）
        out = wiki.wiki_search("mechanics/force-composition", scope="wikilink")
        self.assertIn("mechanics/newton-second-law", out)
        # subject 精确过滤
        out = wiki.wiki_search("mechanics", scope="subject")
        self.assertIn("mechanics/newton-second-law", out)
        self.assertIn("mechanics/force-composition", out)

    def test_b4b_search_no_match_message(self):
        out = wiki.wiki_search("nonexistent_term_zzz", scope="body")
        self.assertIn("（无匹配）", out)

    # -- B5. wiki_index 默认模式：只出报告，不写盘 --

    def test_b5_index_dry_report_does_not_touch_files(self):
        wiki.wiki_write(
            "mechanics/x", "---\ntitle: X\nlevel: basic\n---\n\n# X\n",
        )
        before = (self.tmp / "index.md").read_text(encoding="utf-8")

        out = wiki.wiki_index()  # rebuild=False
        self.assertIn("# wiki_index 扫描摘要", out)
        self.assertIn("概念页总数: 1", out)
        self.assertIn("rebuild=true 才会真的写回", out)

        after = (self.tmp / "index.md").read_text(encoding="utf-8")
        self.assertEqual(before, after, "rebuild=False 不应该修改 index.md")

    # -- B6. wiki_index(rebuild=True) 实际写入 AUTOGEN 段 --

    def test_b6_index_rebuild_injects_autogen_block(self):
        wiki.wiki_write(
            "mechanics/x", "---\ntitle: X\nlevel: basic\n---\n\n# X\n",
        )
        wiki.wiki_write(
            "sources/pep-required-1-ch1",
            "---\nid: sources/pep-required-1-ch1\ntitle: ch1\nlevel: meta\n---\n\n",
        )

        out = wiki.wiki_index(rebuild=True)
        self.assertIn("已重写", out)

        idx = (self.tmp / "index.md").read_text(encoding="utf-8")
        self.assertIn(wiki.INDEX_AUTOGEN_BEGIN, idx)
        self.assertIn(wiki.INDEX_AUTOGEN_END, idx)
        self.assertIn("[[mechanics/x]]", idx)
        self.assertIn("[[sources/pep-required-1-ch1]]", idx)

        ov = (self.tmp / "overview.md").read_text(encoding="utf-8")
        self.assertIn(wiki.INDEX_AUTOGEN_BEGIN, ov)

    # -- B7. 二次 rebuild 是替换不是追加（AUTOGEN 段全局唯一）--

    def test_b7_second_rebuild_is_idempotent_replace(self):
        wiki.wiki_write(
            "mechanics/x", "---\ntitle: X\nlevel: basic\n---\n\n# X\n",
        )
        wiki.wiki_index(rebuild=True)
        idx_after_1 = (self.tmp / "index.md").read_text(encoding="utf-8")

        wiki.wiki_index(rebuild=True)
        idx_after_2 = (self.tmp / "index.md").read_text(encoding="utf-8")

        # 单文件内 AUTOGEN 段恰好出现 1 次（替换语义）
        self.assertEqual(idx_after_2.count(wiki.INDEX_AUTOGEN_BEGIN), 1)
        self.assertEqual(idx_after_2.count(wiki.INDEX_AUTOGEN_END), 1)
        # 内容一致（同样的输入 → 同样的输出）
        self.assertEqual(idx_after_1, idx_after_2)

    # -- D1. 断裂链接被识别 --

    def test_d1_broken_link_detected(self):
        wiki.wiki_write(
            "mechanics/x",
            "---\ntitle: X\nlevel: basic\n---\n\n→ [[mechanics/不存在的页]]\n",
        )
        out = wiki.wiki_index()
        self.assertIn("断裂链接数: 1", out)
        self.assertIn("断裂链接（前 20 条）", out)
        self.assertIn("不存在的页", out)


# ---------------------------------------------------------------------------
# C. mode 隔离（最关键的安全边界）
# ---------------------------------------------------------------------------

class WikiModeIsolationTests(unittest.TestCase):
    """runner 模式下绝不能拿到 wiki_write / wiki_index。"""

    def test_runner_tools_strictly_readonly(self):
        tools = wiki.get_tools("runner")
        names = {t["function"]["name"] for t in tools}
        self.assertEqual(names, {"wiki_read", "wiki_search"})

    def test_runner_executors_strictly_readonly(self):
        execs = wiki.get_executors("runner")
        self.assertEqual(set(execs.keys()), {"wiki_read", "wiki_search"})

    def test_builder_has_all_4_tools(self):
        tools = wiki.get_tools("builder")
        names = {t["function"]["name"] for t in tools}
        self.assertEqual(
            names, {"wiki_read", "wiki_search", "wiki_write", "wiki_index"}
        )

    def test_builder_has_all_4_executors(self):
        execs = wiki.get_executors("builder")
        self.assertEqual(
            set(execs.keys()),
            {"wiki_read", "wiki_search", "wiki_write", "wiki_index"},
        )

    def test_unknown_mode_rejected(self):
        with self.assertRaises(ValueError):
            wiki.get_tools("admin")
        with self.assertRaises(ValueError):
            wiki.get_executors("guest")

    def test_runner_tool_schemas_are_valid_jsonable(self):
        """工具 schema 必须能被 json 序列化（OpenAI tools 协议要求）。"""
        for t in wiki.get_tools("builder"):
            json.dumps(t)  # 抛异常即失败


# ---------------------------------------------------------------------------
# 直接运行入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main(verbosity=2)
