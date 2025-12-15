from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class Pagination:
    """Модель пагинации для всех ответов API"""
    total: int
    perpage: int
    start: int

    @classmethod
    def from_dict(cls, data: dict) -> Optional['Pagination']:
        """Создать объект из словаря"""
        if not data:
            return None

        return cls(
            total=data.get('total', 0),
            perpage=data.get('perpage', 0),
            start=data.get('start', 0)
        )

@dataclass
class Region:
    """Модель региона/локации"""
    id: int
    name: str
    code: str
    base_id: int = 1
    link: Optional[str] = None
    parent: Optional[int] = None
    radius: Optional[int] = None
    announce: Optional[str] = None
    html: Optional[str] = None
    name_loc: Optional[str] = None
    pics: List[str] = field(default_factory=list)

    @property
    def is_root(self) -> bool:
        """Является ли регион корневым (без родителя)"""
        return self.parent is None or self.parent == 0

    @classmethod
    def from_dict(cls, data: dict) -> Optional['Region']:
        """Создать объект из словаря"""
        if not data:
            return None

        return cls(
            id=data.get('id'),
            name=data.get('name', ''),
            code=data.get('code', ''),
            base_id=data.get('base_id', 1),
            link=data.get('link'),
            parent=data.get('parent'),
            radius=data.get('radius'),
            announce=data.get('announce'),
            html=data.get('html'),
            name_loc=data.get('name_loc'),
            pics=data.get('pics', [])
        )

@dataclass
class Hotel:
    """Модель отеля"""
    id: int
    name: str
    base_id: int = 1
    code: Optional[str] = None
    link: Optional[str] = None
    parent: Optional[int] = None
    type: Optional[int] = None
    subtype: Optional[int] = None
    stars: Optional[int] = None
    address: Optional[str] = None
    childage: Optional[str] = None
    latlon: Optional[str] = None
    location: Optional[int] = None
    announce: Optional[str] = None
    html: Optional[str] = None
    indescr: Optional[str] = None
    pics: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> Optional['Hotel']:
        """Создать объект из словаря"""
        if not data:
            return None

        return cls(
            id=data.get('id'),
            name=data.get('name', ''),
            base_id=data.get('base_id', 1),
            code=data.get('code'),
            link=data.get('link'),
            parent=data.get('parent'),
            type=data.get('type'),
            subtype=data.get('subtype'),
            stars=data.get('stars'),
            address=data.get('address'),
            childage=data.get('childage'),
            latlon=data.get('latlon'),
            location=data.get('location'),
            announce=data.get('announce'),
            html=data.get('html'),
            indescr=data.get('indescr'),
            pics=data.get('pics', [])
        )

@dataclass
class HotelRoom:
    """Модель номера в отеле"""
    id: int
    name: str
    base_id: int = 1
    link: Optional[str] = None
    parent: Optional[int] = None
    type: Optional[int] = None
    subtype: Optional[int] = None
    address: Optional[str] = None
    childage: Optional[str] = None
    photo_context_id: Optional[int] = None
    latlon: Optional[str] = None
    location: Optional[int] = None
    announce: Optional[str] = None
    html: Optional[str] = None
    indescr: Optional[str] = None
    pics: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> Optional['HotelRoom']:
        """Создать объект из словаря"""
        if not data:
            return None

        return cls(
            id=data.get('id'),
            name=data.get('name', ''),
            base_id=data.get('base_id', 1),
            link=data.get('link'),
            parent=data.get('parent'),
            type=data.get('type'),
            subtype=data.get('subtype'),
            address=data.get('address'),
            childage=data.get('childage'),
            photo_context_id=data.get('photo_context_id'),
            latlon=data.get('latlon'),
            location=data.get('location'),
            announce=data.get('announce'),
            html=data.get('html'),
            indescr=data.get('indescr'),
            pics=data.get('pics', [])
        )

@dataclass
class RoomPrices:
    """Модель цен номера"""
    schedule_type: int
    sdt: Optional[int] = None
    edt: Optional[int] = None
    dt: Optional[int] = None
    plst: List[any] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> Optional['RoomPrices']:
        """Создать объект из словаря"""
        if not data:
            return None

        return cls(
            schedule_type=data.get('schedule_type', 0),
            sdt=data.get('sdt'),
            edt=data.get('edt'),
            dt=data.get('dt'),
            plst=data.get('plst', [])
        )

@dataclass
class Service:
    """Модель услуги (экскурсии, трансферы и т.п.)"""
    id: int
    name: str
    base_id: int = 1
    link: Optional[str] = None
    type: Optional[int] = None
    subtype: Optional[int] = None
    photo_context_id: Optional[int] = None
    address: Optional[str] = None
    russian_guide: Optional[int] = None
    lunch_included: Optional[int] = None
    private_transport: Optional[int] = None
    tickets_included: Optional[int] = None
    inhttp: Optional[str] = None
    pics: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> Optional['Service']:
        """Создать объект из словаря"""
        if not data:
            return None

        return cls(
            id=data.get('id'),
            name=data.get('name', ''),
            base_id=data.get('base_id', 1),
            link=data.get('link'),
            type=data.get('type'),
            subtype=data.get('subtype'),
            photo_context_id=data.get('photo_context_id'),
            address=data.get('address'),
            russian_guide=data.get('russian_guide'),
            lunch_included=data.get('lunch_included'),
            private_transport=data.get('private_transport'),
            tickets_included=data.get('tickets_included'),
            inhttp=data.get('inhttp'),
            pics=data.get('pics', [])
        )
