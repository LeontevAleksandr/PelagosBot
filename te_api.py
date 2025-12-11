import asyncio
import sys
import os

# Добавляем путь к корню проекта
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from services.pelagos_api import PelagosAPI

async def test_api():
    """Тестирование API клиента"""
    
    # Создаем экземпляр API (без ключа, если он не требуется)
    api_key = '637e638a4447328eebce47b952e7fab0d232e96a7128bfdd485a49ee541376a2'
    api = PelagosAPI(api_key=api_key)
    
    try:
        print("Тестирование API Pelagos...\n")

        # 1. Тест регионов
        print("1. Получение регионов:")
        regions = await api.get_regions()
        print(f"   Найдено регионов: {len(regions)}")

        if regions:
            print(f"   Пример: {regions[0].name} (код: {regions[0].code})")
        
        # 2. Тест корневых регионов
        print("\n2. Получение корневых регионов:")
        root_regions = await api.get_root_regions()
        print(f"   Корневых регионов: {len(root_regions)}")
        
        # 3. Тест отелей - используем конкретный регион из документации
        # Попробуем найти регион Cebu из документации
        test_region = None
        for r in regions:
            if 'cebu' in r.code.lower():
                test_region = r
                break

        if not test_region and regions:
            # Если Cebu не найден, используем первый не-корневой регион
            for r in regions:
                if r.parent and r.parent != 0:
                    test_region = r
                    break

        if test_region:
            print(f"\n3. Отели в регионе '{test_region.name}' (код: {test_region.code}):")

            hotels_result = await api.get_hotels(test_region.code, perpage=3)
            hotels = hotels_result['hotels']
            pagination = hotels_result['pagination']
            
            print(f"   Найдено отелей: {len(hotels)}")
            
            if pagination:
                print(f"   Пагинация: всего {pagination.total}, на странице {pagination.perpage}")
            
            if hotels:
                for i, hotel in enumerate(hotels[:2], 1):
                    print(f"   {i}. {hotel.name} ({hotel.stars or 'без'} звёзд)")
        
        # 4. Тест услуг
        print("\n4. Получение услуг:")
        services_result = await api.get_services(perpage=2)
        services = services_result['services']
        print(f"   Найдено услуг: {len(services)}")
        
        if services:
            print(f"   Пример услуги: {services[0].name}")
        
        # 5. Тест поиска
        print("\n5. Тест поиска отелей:")
        if hotels and len(hotels) > 0:
            search_query = hotels[0].name.split()[0]  # Первое слово названия
            search_results = await api.search_hotels(search_query, limit=2)
            print(f"   Поиск по '{search_query}': найдено {len(search_results)}")
        
        print("\nВсе тесты пройдены успешно!")

    except Exception as e:
        print(f"\nОшибка при тестировании: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Закрываем соединение
        await api.close()

if __name__ == "__main__":
    asyncio.run(test_api())