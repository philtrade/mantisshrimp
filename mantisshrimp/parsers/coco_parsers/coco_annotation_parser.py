__all__ = ["COCOAnnotationParser2"]

from mantisshrimp.imports import *
from mantisshrimp.core import *
from mantisshrimp.parsers.defaults import *
from mantisshrimp.parsers.mixins import *


class COCOAnnotationParser2(MaskRCNNParser, AreaParserMixin, IsCrowdParserMixin):
    def __init__(self, annotations: list):
        self.annotations = annotations

    def __iter__(self):
        yield from self.annotations

    def __len__(self):
        return len(self.annotations)

    def imageid(self, o) -> int:
        return o["image_id"]

    def label(self, o) -> List[int]:
        return [o["category_id"]]

    def bbox(self, o) -> List[BBox]:
        return [BBox.from_xywh(*o["bbox"])]

    def area(self, o) -> List[float]:
        return [o["area"]]

    def mask(self, o) -> List[MaskArray]:
        seg = o["segmentation"]
        if o["iscrowd"]:
            return [RLE.from_coco(seg["counts"])]
        else:
            return [Polygon(seg)]

    def iscrowd(self, o) -> List[bool]:
        return [o["iscrowd"]]
