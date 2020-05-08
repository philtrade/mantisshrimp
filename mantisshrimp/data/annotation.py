# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/04_data.annotations.ipynb (unless otherwise specified).

__all__ = ['Mask', 'MaskFile', 'RLE', 'Polygon', 'BBox', 'ImageInfo', 'Instance', 'Annotation', 'Record', 'ImageParser',
           'AnnotationParser', 'DataParser', 'COCOImageParser', 'COCOAnnotationParser', 'COCOParser', 'show_record']

# Cell
from collections import UserList
from copy import deepcopy
from dataclasses import replace
from ..imports import *
from ..core import *
from .core import *

# Cell
@dataclass
class Mask:
    data: np.ndarray
    def __post_init__(self): self.data = self.data.astype(np.uint8)
    def __len__(self): return len(self.data)
    def __getitem__(self, i): return type(self)(self.data[i])

    def to_tensor(self): return tensor(self.data, dtype=torch.uint8)
    def to_mask(self, h, w): return self
    @property
    def shape(self): return self.data.shape

    @classmethod
    def from_segs(cls, segs, h, w):
        masks = []
        # TODO: Instead of if checks, RLE and Polygon can return with extra dim
        for o in segs:
            m = o.to_mask(h,w).data
            if isinstance(o, (RLE, Polygon)): masks.append(m[None])
            elif isinstance(o, MaskFile): masks.append(m)
            else: raise ValueError(f'Segmented type {type(o)} not supported')
        return cls(np.concatenate([o.to_mask(h, w).data for o in segs]))

# Cell
@dataclass
class MaskFile:
    fp: Union[str, Path]
    def __post_init__(self): self.fp = Path(self.fp)
    def to_mask(self, h, w):
        mask = open_img(self.fp, gray=True)
        obj_ids = np.unique(mask)[1:]
        masks = mask==obj_ids[:, None, None]
        return Mask(masks)

# Cell
@dataclass
class RLE:
    counts: List[int]
    def to_mask(self, h, w):
        erle = mask_utils.frPyObjects([{'counts':self.counts, 'size':[h,w]}], h, w)
        mask = mask_utils.decode(erle).sum(axis=-1) # Sum is for unconnected polygons
        assert mask.max() == 1, 'Probable overlap in polygons'
        return Mask(mask)

# Cell
@dataclass
class Polygon:
    pnts: List[List[int]]
    def to_mask(self, h, w):
        erle = mask_utils.frPyObjects(self.pnts, h, w)
        mask = mask_utils.decode(erle).sum(axis=-1) # Sum is for unconnected polygons
        assert mask.max() == 1, 'Probable overlap in polygons'
        return Mask(mask)

# Cell
@dataclass
class BBox:
    pnts: List[int]
    def __post_init__(self):
        if self.pnts:
            xl,yu,xr,yb = self.pnts
            self.x,self.y,self.h,self.w = xl,yu,(yb-yu),(xr-xl)
            self.area = self.h*self.w
    @property
    def xyxy(self): return self.pnts
    @property
    def xywh(self): return [self.x,self.y,self.w,self.h]
    @classmethod
    def from_xywh(cls, x, y, w, h): return cls([x,y,x+w,y+h])
    @classmethod
    def from_xyxy(cls, xl, yu, xr, yb): return cls([xl,yu,xr,yb])

    def to_tensor(self): return tensor(self.xyxy, dtype=torch.float)

# Cell
@dataclass
class ImageInfo:
    # TODO: Can add width and height
    iid: int
    fp: Union[str, Path]
    h: int
    w: int

    def __post_init__(self): self.fp = Path(self.fp)

# Cell
@dataclass
class Instance:
    oid: int
    bbox: BBox=None
    seg: Polygon=None
    kpts: List=None # TODO
    iscrowd: int=None

# Cell
# TODO: Better way to handle empty oids, bboxes, kpts, segs etcs
@dataclass
class Annotation:
    iid: int
    oids: List[int]
    bboxes: List[BBox]=None
    segs: List[Polygon]=None
    kpts: List[int]=None # TODO
    iscrowds: List[int]=None

#     def __post_init__(self):
#         insts = [self.oids,self.bboxes,self.segs,self.kpts,self.iscrowds]
#         lens = [len(o) for o in insts if notnone(o)]
#         if not allequal(lens): raise ValueError(f'All annotations should have the same size: {lens}')
#         assert len(self.bboxes)==len(self.segs)
    def __getitem__(self, i):
        # TODO: Needs to be refactored?
        bbox = self.bboxes[i] if notnone(self.bboxes) else None
        seg = self.segs[i] if (notnone(self.segs) and len(self.segs)>i) else None # Single mask file can contain multiple masks
        kpts = self.kpts[i] if notnone(self.kpts) else None
        iscrowd = self.iscrowds[i] if notnone(self.iscrowds) else None
        return Instance(oid=self.oids[i],bbox=bbox,seg=seg,kpts=None,iscrowd=iscrowd) #kpts None

# Cell
@dataclass
class Record:
    iinfo: ImageInfo
    annot: Annotation

    def new(self, *, iinfo=None, annot=None):
        iinfo = replace(self.iinfo, **(iinfo or {}))
        annot = replace(self.annot, **(annot or {}))
        return replace(self, iinfo=iinfo, annot=annot)

    def to_rcnn_target(self):
        r = {
            'image_id': tensor(self.iinfo.iid, dtype=torch.int64),
            'labels': tensor(self.annot.oids),
            'boxes': torch.stack([o.to_tensor() for o in self.annot.bboxes]),
        #     'keypoints': self.annot.kpts.to_tensor(), # TODO
            'area': tensor([o.area for o in self.annot.bboxes]),
            'iscrowd': tensor(self.annot.iscrowds, dtype=torch.uint8),
        }
        segs = self.annot.segs
        if notnone(segs):
            if isinstance(segs, Mask): m = segs
            elif isinstance(segs, list): m = Mask.from_segs(segs, self.iinfo.h, self.iinfo.w)
            else: raise ValueError(f'Type for masks {type(masks)} not supported')
            r['masks'] = m.to_tensor()
        # TODO: Check all shapes have N
        return r

# Cell
class ImageParser:
    def __init__(self, data, source): self.data,self.source = data,Path(source)
    def __iter__(self): yield from self.data
    def __len__(self): return len(self.data)

    def prepare(self, o): pass
    def iid(self, o): raise NotImplementedError
    def file_path(self, o): raise NotImplementedError
    def height(self, o): raise NotImplementedError
    def width(self, o): raise NotImplementedError

    def parse(self):
        xs = []
        for o in tqdm(self):
            self.prepare(o)
            xs.append(ImageInfo(iid=self.iid(o), fp=self.file_path(o),
                                h=self.height(o), w=self.width(o)))
        return xs

# Cell
class AnnotationParser:
    def __init__(self, data, source): self.data,self.source = data,source
    def __iter__(self): yield from self.data
    def __len__(self): return len(self.data)
    # Methods to override
    def prepare(self, o): pass
    def bbox(self, o): pass
    def iid(self, o): pass
    def seg(self, o): pass
    def iscrowd(self, o): return 0

    # TODO: Refactor
    def parse(self):
        res = defaultdict(dict)
        iids = set()
        bboxes = defaultdict(list)
        segs = defaultdict(list)
        oids = defaultdict(list)
        iscrowds = defaultdict(list)
        for o in tqdm(self):
            self.prepare(o)
            iid = self.iid(o)
            bbox = self.bbox(o)
            seg = self.seg(o)
            oid = self.oid(o)
            iscrowd = self.iscrowd(o)
            if oid is not None: oids[iid].extend(L(oid))
            if bbox is not None: bboxes[iid].extend(L(bbox))
            if seg is not None: segs[iid].extend(L(seg))
            if iscrowd is not None: iscrowds[iid].extend(L(iscrowd))
            iids.add(iid)
        for d in [bboxes,segs,oids,iscrowds]: d.default_factory = lambda: None
        return [Annotation(i, oids[i], bboxes=bboxes[i], segs=segs[i], iscrowds=iscrowds[i]) for i in iids]

# Cell
class DataParser:
    def __init__(self, data, source): self.data,self.source=data,source
    def get_img_parser(self, o, source): raise NotImplementedError
    def get_annot_parser(self, o, source): raise NotImpletedError

    def parse(self):
        imgs = L(self.get_img_parser(self.data, self.source).parse())
        annots = L(self.get_annot_parser(self.data, self.source).parse())
        # Remove imgs that don't have annotations
        img_iids = set(imgs.attrgot('iid'))
        valid_iids = set(annots.attrgot('iid'))
        if not valid_iids.issubset(img_iids):
            raise ValueError(f'iids {valid_iids-img_iids} present in annotations but not in images')
        valid_imgs = imgs.filter(lambda o: o.iid in valid_iids)
        print(f"Removed {len(imgs)-len(valid_iids)} images that don't have annotations")
        # Sort and get items
        assert len(annots)==len(valid_imgs)
        valid_imgs.sort(attrgetter('iid'))
        annots.sort(attrgetter('iid'))
        return [Record(iinfo,annot) for iinfo,annot in zip(valid_imgs,annots)]

# Cell
class COCOImageParser(ImageParser):
    def iid(self, o): return o['id']
    def file_path(self, o): return self.source/o['file_name']
    def height(self, o): return o['height']
    def width(self, o): return o['width']

# Cell
class COCOAnnotationParser(AnnotationParser):
    def iid(self, o):  return o['image_id']
    def oid(self, o): return o['category_id']
    def bbox(self, o): return BBox.from_xywh(*o['bbox'])
    def iscrowd(self, o): return o['iscrowd']
    def seg(self, o):
        seg = o['segmentation']
        if o['iscrowd']: return RLE(seg['counts'])
        else: return Polygon(seg)

# Cell
class COCOParser(DataParser):
    def get_img_parser(self, o, source): return COCOImageParser(o['images'], source)
    def get_annot_parser(self, o, source): return COCOAnnotationParser(o['annotations'], source)

# Cell
from matplotlib import patches
from matplotlib.collections import PatchCollection

# Cell
def show_record(record, im=None, id2cat=None, bbox=False, fontsize=18, ax=None, **kwargs):
    'From github.com/cocodataset/cocoapi/blob/master/PythonAPI/pycocotools/coco.py#L233'
    im = im if notnone(im) else open_img(record.iinfo.fp)
    height,width,_ = im.shape
    ax = show_img(im, ax=ax, **kwargs)
    ax.set_autoscale_on(False)
    polygons = []
    color = []
    for ann in record.annot:
        c = (np.random.random((1, 3))*0.6+0.4).tolist()[0]
        # Assert both seg and masks are not present, or unify view
        if ann.seg is not None:
            if isinstance(ann.seg, Polygon):
                for seg in ann.seg.pnts:
                    poly = np.array(seg).reshape((int(len(seg)/2), 2))
                    polygons.append(patches.Polygon(poly))
                    color.append(c)
            elif isinstance(ann.seg, RLE):
                if isinstance(ann.seg.counts, list):
#                     rle = mask_utils.frPyObjects([ann.seg.counts], height, width)
                    m = ann.seg.to_mask(height, width).data
                else:
                    raise NotImplementedError
    #                 rle = [ann['segmentation']]
#                 m = mask_utils.decode(rle)
                if ann.iscrowd == 1: color_mask = np.array([2.0,166.0,101.0])/255
                if ann.iscrowd == 0: raise NotImplementedError # TODO: I'm not sure how to handle this case
    #                 color_mask = np.random.random((1, 3)).tolist()[0]
            elif isinstance(ann.seg, MaskFile):
                masks = ann.seg.to_mask(height, width).data
                color_masks = np.random.random((masks.shape[0], 3))
                imgs = np.ones((*masks.shape, 3))
                for img,m,color_mask in zip(imgs,masks,color_masks):
                    for i in range(3):
                        img[:,:,i] = color_mask[i]
                    ax.imshow(np.dstack((img, m*0.5)))
            elif isinstance(ann.seg, Mask):
                m = ann.seg.data
                color_mask = np.random.random(3)
            else: raise ValueError(f'Not supported type: {type(ann.seg)}')
            if isinstance(ann.seg, RLE) or isinstance(ann.seg, Mask):
                img = np.ones( (m.shape[0], m.shape[1], 3) )
                for i in range(3):
                    img[:,:,i] = color_mask[i]
                ax.imshow(np.dstack( (img, m*0.5) ))
        if ann.kpts and type(ann['keypoints']) == list:
            raise NotImplementedError
            # turn skeleton into zero-based index
    #                     sks = np.array(self.loadCats(ann['category_id'])[0]['skeleton'])-1
    #                     kp = np.array(ann['keypoints'])
    #                     x = kp[0::3]
    #                     y = kp[1::3]
    #                     v = kp[2::3]
    #                     for sk in sks:
    #                         if np.all(v[sk]>0):
    #                             plt.plot(x[sk],y[sk], linewidth=3, color=c)
    #                     ax.plot(x[v>0], y[v>0],'o',markersize=8, markerfacecolor=c, markeredgecolor='k',markeredgewidth=2)
    #                     ax.plot(x[v>1], y[v>1],'o',markersize=8, markerfacecolor=c, markeredgecolor=c, markeredgewidth=2)

        if bbox:
            [bx, by, bw, bh] = ann.bbox.xywh
            poly = [[bx, by], [bx, by+bh], [bx+bw, by+bh], [bx+bw, by]]
            np_poly = np.array(poly).reshape((4,2))
            polygons.append(patches.Polygon(np_poly))
            color.append(c)
            name = ann.oid if id2cat is None else id2cat[ann.oid]
            ax.text(bx+1, by-2, name, fontsize=fontsize, color='white', va='bottom',
                    bbox=dict(facecolor=c, edgecolor=c, pad=2, alpha=.9))

    p = PatchCollection(polygons, facecolor=color, linewidths=0, alpha=0.4)
    ax.add_collection(p)
    p = PatchCollection(polygons, facecolor='none', edgecolors=color, linewidths=2)
    ax.add_collection(p)