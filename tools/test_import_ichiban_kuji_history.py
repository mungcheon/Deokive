from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from import_ichiban_kuji_history import _extract_item_blocks, _extract_tier, _strip_tier


class ImportIchibanKujiHistoryTests(unittest.TestCase):
    def test_extracts_boxed_numbered_tier(self):
        name = "\u3010\u30d5\u30a1\u30a4\u30bf\u30fc\u30dc\u30c3\u30af\u30b9\u30111\u7b49 \u5bfe\u6c7a\u30af\u30c3\u30b7\u30e7\u30f3"

        self.assertEqual(_extract_tier(name), "\u3010\u30d5\u30a1\u30a4\u30bf\u30fc\u30dc\u30c3\u30af\u30b9\u30111\u7b49")
        self.assertEqual(_strip_tier(name), "\u5bfe\u6c7a\u30af\u30c3\u30b7\u30e7\u30f3")

    def test_existing_letter_tier_still_works(self):
        self.assertEqual(_extract_tier("A\u8cde \u30d5\u30a3\u30ae\u30e5\u30a2"), "A\u8cde")

    def test_extracts_boxed_double_chance_tier(self):
        name = "\u3010\u30af\u30a8\u30b9\u30c8\u30dc\u30c3\u30af\u30b9\u3011\u30c0\u30d6\u30eb\u30c1\u30e3\u30f3\u30b9\u30ad\u30e3\u30f3\u30da\u30fc\u30f3 \u30b9\u30da\u30b7\u30e3\u30eb\u30bf\u30da\u30b9\u30c8\u30ea\u30fc"

        self.assertEqual(
            _extract_tier(name),
            "\u3010\u30af\u30a8\u30b9\u30c8\u30dc\u30c3\u30af\u30b9\u3011\u30c0\u30d6\u30eb\u30c1\u30e3\u30f3\u30b9\u30ad\u30e3\u30f3\u30da\u30fc\u30f3",
        )
        self.assertEqual(_strip_tier(name), "\u30b9\u30da\u30b7\u30e3\u30eb\u30bf\u30da\u30b9\u30c8\u30ea\u30fc")

    def test_item_blocks_prefer_gallery_product_image_over_heading_decoration(self):
        source = """
        <section>
          <div class="itemColList">
            <h4 class="name sp"><img src="https://example.test/decorative-prize-title.png">A賞 フィギュア</h4>
            <div class="itemColGallery item-gallery slider-parent">
              <ul class="slider-item slider-images">
                <li><a href="https://assets.1kuji.com/uploads/product_item/image/123/item.jpg">
                  <img alt="img1" src="https://assets.1kuji.com/uploads/product_item/image/123/item.jpg" />
                </a></li>
              </ul>
            </div>
            <h4 class="name pc"><img src="https://example.test/decorative-prize-title.png">A賞 フィギュア</h4>
          </div>
        </section>
        """

        self.assertEqual(
            _extract_item_blocks(source, "https://1kuji.com/products/demo"),
            [("https://assets.1kuji.com/uploads/product_item/image/123/item.jpg", "A賞 フィギュア")],
        )


if __name__ == "__main__":
    unittest.main()
