from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class Pagination:
    """Модель пагинации для всех ответов API"""
    total: int
    perpage: int
    start: int

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
    
@dataclass
class RoomPrices:
    """Модель цен номера"""
    schedule_type: int
    per: int
    period: int
    fill: int
    grp: int
    price: float
    sdt: Optional[int] = None
    edt: Optional[int] = None
    dt: Optional[int] = None
    alt: Optional[str] = None
    plst: List[any] = field(default_factory=list)

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