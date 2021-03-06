__all__ = ["DetrBBoxParser", "DetrMaskParser"]

from mantisshrimp.imports import *
from mantisshrimp import *


class DetrBBoxParser(
    DefaultImageInfoParser, FasterRCNNParser, AreaParserMixin, IsCrowdParserMixin, ABC
):
    """
    This parser contain all the required fields for using Detr for bbox detection.
    """


class DetrMaskParser(DetrBBoxParser, MaskRCNNParser, ABC):
    """
    This parser contain all the required fields for using Detr for bbox detection.
    """
