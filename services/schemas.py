from dataclasses import dataclass, field
from typing import Optional, List, Any

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
    ord: Optional[int] = None  # Рейтинг отеля (объединяет рейтинг, продажи, отзывы)

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
            pics=data.get('pics', []),
            ord=data.get('ord', 0)
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
    plst: List[Any] = field(default_factory=list)

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
class Service: # dont use
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
    daily: Optional[int] = None
    inhttp: Optional[str] = None
    pics: List[str] = field(default_factory=list)
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    current: Optional[dict] = None  # Объект с текущей ценой

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
            daily=data.get('daily'),
            inhttp=data.get('inhttp'),
            pics=data.get('pics', []),
            min_price=data.get('min_price'),
            max_price=data.get('max_price'),
            current=data.get('current')
        )

@dataclass
class ExcursionEvent:
    """Модель события экскурсии (конкретная дата проведения)"""
    id: int
    service_id: int
    base_id: int
    sdt: int  # Start datetime (Unix timestamp)
    duration: int = 0
    time_fixed: int = 0
    price: float = 0
    status: int = 0
    cdt: Optional[int] = None
    dt: Optional[int] = None
    hue: Optional[int] = None
    pax: int = 0
    id_url: Optional[str] = None
    service: Optional[Service] = None

    @classmethod
    def from_dict(cls, data: dict) -> Optional['ExcursionEvent']:
        """Создать объект из словаря"""
        if not data:
            return None

        # Парсим вложенный service если есть
        service_data = data.get('service')
        service = None
        if service_data:
            # Создаем упрощенную версию Service для экскурсий
            service = Service(
                id=service_data.get('id'),
                name=service_data.get('name', ''),
                base_id=service_data.get('base_id', 1),
                link=service_data.get('link'),
                type=service_data.get('type'),
                subtype=service_data.get('subtype'),
                russian_guide=service_data.get('russian_guide'),
                min_price=service_data.get('min_price'),
                max_price=service_data.get('max_price'),
                current=service_data.get('current')
            )
            # Добавляем дополнительные поля
            service.html = service_data.get('html')
            service.location = service_data.get('location')
            service.ord = service_data.get('ord', 0)
            service.pic = service_data.get('pic')
            service.pics = service_data.get('pics', [])  # ИСПРАВЛЕНИЕ: добавляем массив фотографий
            service.rlst = service_data.get('rlst', [])  # ИСПРАВЛЕНИЕ: добавляем расписание с ценами

        return cls(
            id=data.get('id'),
            service_id=data.get('service_id'),
            base_id=data.get('base_id', 1),
            sdt=data.get('sdt'),
            duration=data.get('duration', 0),
            time_fixed=data.get('time_fixed', 0),
            price=data.get('price', 0),
            status=data.get('status', 0),
            cdt=data.get('cdt'),
            dt=data.get('dt'),
            hue=data.get('hue'),
            pax=data.get('pax', 0),
            id_url=data.get('id_url'),
            service=service
        )

@dataclass
class ExcursionDay:
    """Модель дня в календаре экскурсий"""
    dt: int  # Unix timestamp начала дня
    edt: int  # Unix timestamp конца дня
    day: int
    mon: int
    year: str
    wday: int  # День недели
    date: str  # Дата в формате DD.MM.YYYY
    smon: str  # Название месяца
    time: str  # Время в формате DD.MM.YYYY HH:MM
    events: List[ExcursionEvent] = field(default_factory=list)
    fut: int = 0  # Будущая дата
    other: bool = False  # Относится к другому месяцу
    eidx: int = 0

    @classmethod
    def from_dict(cls, data: dict) -> Optional['ExcursionDay']:
        """Создать объект из словаря"""
        if not data:
            return None

        # Парсим события
        events = []
        for event_data in data.get('events', []):
            event = ExcursionEvent.from_dict(event_data)
            if event:
                events.append(event)

        return cls(
            dt=data.get('dt'),
            edt=data.get('edt'),
            day=data.get('day'),
            mon=data.get('mon'),
            year=data.get('year', ''),
            wday=data.get('wday'),
            date=data.get('date', ''),
            smon=data.get('smon', ''),
            time=data.get('time', ''),
            events=events,
            fut=data.get('fut', 0),
            other=data.get('other', False),
            eidx=data.get('eidx', 0)
        )

@dataclass
class ExcursionMonth:
    """Модель месяца в календаре экскурсий"""
    name: str
    year: str
    days: List[ExcursionDay] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> Optional['ExcursionMonth']:
        """Создать объект из словаря"""
        if not data:
            return None

        # Парсим дни
        days = []
        for day_data in data.get('days', []):
            day = ExcursionDay.from_dict(day_data)
            if day:
                days.append(day)

        return cls(
            name=data.get('name', ''),
            year=data.get('year', ''),
            days=days
        )

@dataclass
class Transfer:
    """Модель трансфера"""
    id: int
    name: str
    base_id: int = 1
    link: Optional[str] = None
    type: Optional[int] = None
    subtype: Optional[int] = None
    location: Optional[int] = None
    photo_context_id: Optional[int] = None
    russian_guide: Optional[int] = None
    private_transport: Optional[int] = None
    group_ex: Optional[int] = None
    inhttp: Optional[str] = None
    pics: List[Any] = field(default_factory=list)
    cdt: Optional[int] = None
    dt: Optional[int] = None
    ord: Optional[int] = None
    score: Optional[int] = None

    @classmethod
    def from_dict(cls, data: dict) -> Optional['Transfer']:
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
            location=data.get('location'),
            photo_context_id=data.get('photo_context_id'),
            russian_guide=data.get('russian_guide'),
            private_transport=data.get('private_transport'),
            group_ex=data.get('group_ex'),
            inhttp=data.get('inhttp'),
            pics=data.get('pics', []),
            cdt=data.get('cdt'),
            dt=data.get('dt'),
            ord=data.get('ord'),
            score=data.get('score')
        )
