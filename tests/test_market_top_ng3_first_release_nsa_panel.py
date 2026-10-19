from __future__ import annotations

import unittest

from research.build_market_top_ng3_first_release_nsa_panel_1986_1988 import (
    parse_table1_aggregate_geometry,
)


def row(label: str, y: float, values: list[tuple[float, str]], label_x: float = 58.0):
    spans = [{"text": label, "x": label_x, "y": y, "font_size": 7.0}]
    spans.extend(
        {"text": text, "x": x, "y": y + (0.12 if i % 2 else 0.0), "font_size": 7.0}
        for i, (x, text) in enumerate(values)
    )
    return spans


class MarketTopNG3FirstReleaseNSAPanelTests(unittest.TestCase):
    def test_finished_goods_geometry(self):
        spans = row(
            "Finished goods",
            685.5,
            [
                (282.0, "100.000"),
                (329.0, "291.8"),
                (359.0, "295.0"),
                (390.0, "296.3"),
                (425.0, "2.6"),
                (453.0, "0.4"),
                (484.0, "0.4"),
            ],
        )
        x = parse_table1_aggregate_geometry(spans, "finished_goods")
        self.assertEqual(x["status"], "PARSED_GEOMETRY")
        self.assertEqual(x["relative_importance"], 100.0)
        self.assertEqual(x["january_level_nsa"], 291.8)
        self.assertEqual(x["previous_month_level_nsa"], 295.0)
        self.assertEqual(x["current_month_level_nsa"], 296.3)
        self.assertEqual(x["yoy_nsa_pct"], 2.6)
        self.assertEqual(x["mom_nsa_pct"], 0.4)

    def test_intermediate_geometry(self):
        spans = row(
            "Intermediate materials, supplies and components.",
            685.5,
            [
                (282.0, "100.000"),
                (329.0, "307.0"),
                (359.0, "310.9"),
                (390.0, "312.7"),
                (425.0, "2.0"),
                (453.0, "0.6"),
            ],
        )
        x = parse_table1_aggregate_geometry(spans, "intermediate_goods")
        self.assertEqual(x["status"], "PARSED_GEOMETRY")
        self.assertEqual(x["current_month_level_nsa"], 312.7)
        self.assertEqual(x["yoy_nsa_pct"], 2.0)

    def test_superscript_at_same_x_is_ignored(self):
        spans = row(
            "Finished goods",
            680.9,
            [
                (280.8, "100.000"),
                (329.5, "294.7"),
                (359.9, "296.2"),
                (390.4, "292.3"),
                (419.8, "-0.1"),
                (447.7, "-1.3"),
            ],
        )
        spans.append(
            {"text": "7", "x": 280.8, "y": 680.9, "font_size": 4.55}
        )
        x = parse_table1_aggregate_geometry(spans, "finished_goods")
        self.assertEqual(x["status"], "PARSED_GEOMETRY")
        self.assertEqual(x["relative_importance"], 100.0)
        self.assertEqual(x["current_month_level_nsa"], 292.3)
        self.assertEqual(x["yoy_nsa_pct"], -0.1)

    def test_duplicate_numeric_column_fails_closed(self):
        spans = row(
            "Finished goods",
            680.0,
            [
                (282.0, "100.000"),
                (329.0, "291.8"),
                (359.0, "295.0"),
                (390.0, "296.3"),
                (425.0, "2.6"),
                (453.0, "0.4"),
            ],
        )
        spans.append({"text": "999.9", "x": 391.0, "y": 680.0, "font_size": 7.0})
        x = parse_table1_aggregate_geometry(spans, "finished_goods")
        self.assertEqual(x["status"], "COLUMN_GEOMETRY_INCOMPLETE")
        self.assertEqual(
            x["columns"]["current_month_level_nsa"]["status"],
            "AMBIGUOUS_COLUMN",
        )

    def test_invalid_label_fails_closed(self):
        with self.assertRaises(ValueError):
            parse_table1_aggregate_geometry([], "unknown")


if __name__ == "__main__":
    unittest.main()
