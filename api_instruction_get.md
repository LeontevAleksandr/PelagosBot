Пример кода для получения информации через API
Ключ API можно получить здесь: https://app.pelagos.ru/my-apikeys/

Примеры URL запросов - в самом низу. По сути всё что нужно для успешного совершения запроса - добавить заголовок X-Key со значением вашего ключа API.

function api_request($url) {
    // В этом примере - GuzzleHttp, но можно использовать file_get_contents или curl
    $client = new \GuzzleHttp\Client(); 

    $headers = [
        "X-Key" => PELAGOS_API_KEY, // в этой константе ваш ключ API
    ];

    try {
        $response = $client->request('GET', $url, [
            'headers' => $headers,
        ]);

        $code = $response->getStatusCode();
        echo "HTTP response code: {$code}\r\n";
        echo "Headers:\r\n";
        $rheaders = $response->getHeaders();
        foreach ($rheaders as $n => $v) {
            foreach ($v as $val) {
                echo $n.": ".$val."\r\n";
            }
        }
        echo "\r\n";
        $body = $response->getBody();

        echo $body;

    } catch(\Exception $e) {
        echo "Error: \r\n";
        $msg = $e->getMessage();
        echo $msg."\r\n";
        echo $e->getTraceAsString()."\r\n";
        exit;
    }
}

// Получать список отелей. Параметры: start - начало пагинации (0 - первый элемент), perpage - количество отелей в ответе
api_request("https://app.pelagos.ru/export-hotels/cebu/?start=10&perpage=10");
// Получить XML файл. Параметры: cache=1 - скачать кэшированный файл. Без параметра - создать файл заново и вернуть.
api_request("https://app.pelagos.ru/export-rooms-xml/?cache=1");
// Получить список номеров по ID отеля.  /export-hotels-rooms/{hotel_id}/
api_request("https://app.pelagos.ru/export-hotels-rooms/240/");
// Получить ценники номера по ID номера. /export-hotels-rooms-prices/{room_id}/
api_request("https://app.pelagos.ru/export-hotels-rooms-prices/717/");
// Получить подробную информацию об отеле, в т.ч. фото
api_request("https://app.pelagos.ru/export-hotel/240/");
// Получить подробную информацию об услугах
api_request("https://app.pelagos.ru/export-services-xml/?cache=1");
JSON API
Список регионов
https://app.pelagos.ru/export-locations/

Структура ответа
Условные обозначения: # - число, $ - текст, [...] - массив объектов

{code: "OK", locations: [
{id: #, name: $, base_id: #, code: $, link: $, parent: #, 
radius: #, announce: $, html: $, name_loc: $, pics: [...]}, ...
]}
либо

{code: "Error", message: $ /* текст ошибки */}
Значения полей
id - уникальный идентификатор региона в базе данных

name - название региона

base_id - числовой идентификатор базы (Филиппины, Гонконг, и т.п.). Для Филиппин это 1.

code - URL-код

link - внутренний код (не используется)

parent - идентифиактор вышестоящего объекта (регионы выстроены в иерархическую структуру)

radius - условный радиус (величина) региона

announce - краткое описание региона

html - полное описание региона в HTML

name_loc - локализованное (местное) название региона

pics - список изображений

О списке изображений
(используется также в других функциях)

Массив объектов следующего содержания:

id - уникальный числовой идентификатор изображения

md5 - уникальный случайный текстовый идентификатор изображения, основной идентификтор, который используется для получения изображения

size - размер файла полного изображения

filename - имя файла

type - MIME тип изображения

thumb - параметры, с которыми было загружено изображение

ext - расширение имени файла

Как получить собственно сам файл изображения: вставьте параметры в следущий шаблон URL:

https://app.pelagos.ru/pic/{md5}/{filename} - для полного изображения (без уменьшения)

На самом деле важен только параметр md5, поэтому точно такой же файл можно получить и, например, вот так:

https://app.pelagos.ru/pic/{md5}/{md5}.{ext} или https://app.pelagos.ru/pic/{md5}/image.{ext}

Также есть способ получить уменьшенное изображение (thumbnail):

https://app.pelagos.ru/thumb/{md5}/{filename} - тамбнейл, созданный при загрузке фотографии (с теми параметрами, которые указаны в thumb)

https://app.pelagos.ru/freepic/{md5}/{filename}?opts=inner&size={width}x{height} - тамбнейл прозвольного размера, где width и height соответственно ширина и высота в пикселях. Если не указать opts=inner, то изображение нужных пропорций будет вырезано из середины оригинального изображения. Если же указать opts=inner, то тогда оригинальное изображение будет уменьшено (но не увеличено) до размера, который вписывается в указанные габариты.

Список отелей
https://app.pelagos.ru/export-hotels/<location_id>/

Параметры URL
location_id - буквенный код острова (региона), списки отелей сгруппированы по регионам. Буквенный код берётся из параметра code объекта в массиве locations в ответе API Список регионов.

Параметры GET
perpage - число, предельное число отелей в ответе

start - с какого отеля начинать отбор (первый отель - 0)

Структура ответа
{code: "OK", hotels: [
{id: #, name: $, base_id: #, link: $, parent: #, type: #, subtype: #,
address: $, childage: $, photo_context_id: #, latlon: $, address: $, 
location: #, announce: $, html: $c, indescr: $, pics: [...]}, ...
], "pages": {
total: #, perpage: #, start: #
}}
либо ответ с ошибкой (см. выше)

Значения полей
id - уникальный идентификатор объекта (отеля) в базе данных

name - название отеля

base_id - числовой идентификатор базы (Филиппины, Гонконг, и т.п.). Для Филиппин это 1.

code - URL-код

link - внутренний код (не используется)

parent - идентифиактор вышестоящего объекта

type - тип объекта. Типы объектов: https://app.pelagos.ru/json-loadenum/objecttype/

subtype - подтип объекта (второй тип)

stars - звёздность

address - адрес отеля

childage - возраст для детей (люди какого возраста считаются детьми для целей расчёта стоимости размещения)

latlon - географические координаты, широта и долгота

location - числовой идентификатор региона (острова)

announce - краткое описание отеля

html - полное описание отеля в HTML (внешнее)

indescr - описание отеля внутреннее на английском (условия)

pics - список изображений

Объект pages (пагинация)
total - сколько всего объектов в списке

perpage - максимальное число объектов на странице (в данном запросе / ответе)

start - с какого по счёту (начиная с 0) объекта начинается список объектов в ответе

Список номеров в отеле
https://app.pelagos.ru/export-hotels-rooms/{hotel_id}/

Параметры URL
hotel_id - числовой код отеля. Берётся из параметра id объекта в массиве hotels в ответе API Список отелей.

Структура ответа
{code: "OK", rooms: [
{id: #, name: $, base_id: #, link: $, parent: #, type: #, subtype: #,
address: $, childage: $, photo_context_id: #, latlon: $, address: $, 
location: #, announce: $, html: $c, indescr: $, pics: [...]}, ...
], "pages": {
total: #, perpage: #, start: #
}}
либо ответ с ошибкой (см. выше)

Значения полей
Значения полей те же, что и для отелей (Список отелей), т.к. это строки той же самой таблицы базы данных. У отдельных номеров как правило нет собственного адреса, географических координат, описаний, и фотографии, в некоторых случаях некоторые поля (особенно описание и фото) бывают заполнены.

Пагинатора в этой функции нет, выдаётся полный список номеров одного отеля.

Список цен номера
https://app.pelagos.ru/export-hotels-rooms-prices/{room_id}/

Параметры URL
room_id - числовой код номера. Берётся из параметра id объекта в массиве rooms в ответе API Список номеров в отеле.

Структура ответа
{code: "OK", prices: [
{id: #, schedule_type: 2, sdt: #, edt: #, dt: #, plst: [
{per: #, period: #, fill: #, grp: #, price: #, alt: $, dt: #}...]}, ...
]}
либо ответ с ошибкой (см. выше)

Значения полей
schedule_type - тип расписания. Как правило, «2: Точные даты». Весь список вариантов тут: https://app.pelagos.ru/json-loadenum/scheduletype/

sdt - для расписания «Точные даты» - Unix timestamp начала периода, в который действуют цены

edt - Unix timestamp окончания периода действия цены

dt - Unix timestamp время изменения ценника

plst - массив объектов «Компоненты ценника»:

per - единицы измерения или «за что платим» (объект, человек, питание). Список вариантов: https://app.pelagos.ru/json-loadenum/per/

period - период, за который платим (день, час, раз). Список вариантов: https://app.pelagos.ru/json-loadenum/period/

fill - заполнение. 1 - за одного, 2 - за двоих (если цена за номер), и так далее. Если 0, то считается что за 2.

grp - в составе группы из grp человек. Для экскурсий. Такая цена будет применяться в том случае, если общий размер сборной группы меньше или равно данному параметру.

price - цена в долларах США

alt - альтернативное текстовое описание цены (условий), к примеру «ala carte» или «inc».

Услуги (экскурсии, трансферы и т.п.)
https://app.pelagos.ru/export-services/

Параметры GET
perpage - число, предельное число отелей в ответе

start - с какого отеля начинать отбор (первый отель - 0)

id - отобрать только одну услугу с указанным ID

search - искать услуги по тексту (запрос к БД будет like '%{$search}%)

Структура ответа
{code: "OK", services: [
{id: #, name: $, base_id: #, link: $, type: #, subtype: #,
photo_context_id: #, address: $, russian_guide: #, lunch_included: #, 
private_transport #, tickets_included #, inhttp $, pics: [...]}, ...
], "pages": {
total: #, perpage: #, start: #
}}
либо ответ с ошибкой (см. выше)

Любые объекты (отели, номера, услуги, экскурсии, трансферы и т.п.)
https://app.pelagos.ru/export-objects/

Параметры GET
perpage - число, предельное число отелей в ответе

start - с какого отеля начинать отбор (первый отель - 0)

id - отобрать только одну услугу с указанным ID

search - искать услуги по тексту (запрос к БД будет like '%{$search}%)