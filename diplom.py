import pandas as pd
import networkx as nx
from geopy.distance import geodesic
from datetime import datetime

def load_data(file_path):
    routes_rail = pd.read_excel(file_path, sheet_name='Маршрут ЖД')
    routes_sea = pd.read_excel(file_path, sheet_name='Маршрут Море')
    warehouses = pd.read_excel(file_path, sheet_name='Склады')
    schedule = pd.read_excel(file_path, sheet_name='Расписание')  
    return routes_rail, routes_sea, warehouses, schedule

def add_sea_routes_to_graph(G, routes_sea, schedule, current_time):
    for _, sea_route in routes_sea.iterrows():
        origin = sea_route['Пункт отправки']
        destination = sea_route['Место назначения']

        for _, row in schedule.iterrows():
            origin_etd = f'{origin} ETD'
            destination_eta = f'{destination} ETA'
            if origin_etd in schedule.columns and destination_eta in schedule.columns:
                etd = row[origin_etd]
                eta = row[destination_eta]

                if pd.notnull(etd) and pd.notnull(eta) and etd >= current_time:
                    travel_hours = (eta - etd).total_seconds() / 3600
                    G.add_edge(origin, destination, weight=travel_hours,
                               voyage=row['VOY.NO.'], eta=eta.strftime('%Y-%m-%d'))


def find_shortest_path(G, source, target):
    try:
        path = nx.shortest_path(G, source=source, target=target, weight='weight')
        path_details = []
        for i in range(len(path)-1):
            edge_data = G.get_edge_data(path[i], path[i+1])
            voyage = edge_data.get('voyage', 'N/A') 
            eta = edge_data.get('eta', 'N/A')
            path_details.append((path[i], path[i+1], voyage, eta))
        length = nx.shortest_path_length(G, source=source, target=target, weight='weight')
        return path_details, length
    except (nx.NetworkXNoPath, nx.NodeNotFound) as e:
        return None, None
def find_closest_station_to_warehouse(routes_rail, warehouse_coords):
    """Поиск ближайшей железнодорожной станции к складу."""
    min_distance = float('inf')
    closest_station = None
    for _, route in routes_rail.iterrows():
        station_coords = (route['Широта'], route['Долгота'])  # Эти данные нужно добавить в таблицу маршрутов ЖД
        distance = geodesic(station_coords, warehouse_coords).kilometers
        if distance < min_distance:
            min_distance = distance
            closest_station = route['Место назначения']
    return closest_station, min_distance

# Функция добавления информации о складах и автомобильных путях до складов 
def add_warehouse_info_to_routes(routes_rail, warehouses):
    average_speed_km_h = 60  # Средняя скорость автомобильного транспорта в км/ч
    for index, route in routes_rail.iterrows():
        destination_coords = (route['Широта'], route['Долгота'])
        closest_warehouse, distance_to_warehouse = find_closest_station_to_warehouse(warehouses, destination_coords)
        routes_rail.at[index, 'Ближайший склад'] = closest_warehouse
        routes_rail.at[index, 'Расстояние до склада (км)'] = distance_to_warehouse
        # Расчет предполагаемого времени автомобильной перевозки до склада
        estimated_drive_time = distance_to_warehouse / average_speed_km_h
        routes_rail.at[index, 'Время до склада (ч)'] = estimated_drive_time
   
def build_graph(routes_rail, routes_sea, warehouses, schedule):
    G = nx.DiGraph()
    current_time = datetime.now()

    # Добавление морских маршрутов из листа "Расписание"
    add_sea_routes_to_graph(G, routes_sea, schedule, current_time)

    # Добавление железнодорожных маршрутов
    for _, row in routes_rail.iterrows():
        G.add_edge(row['Город 1'], row['Место назначения'], weight=row['Время (по участковой скорости поезда)'])

    # Добавление автомобильных путей от станций до складов
    average_speed_km_h = 60
    for _, warehouse in warehouses.iterrows():
        warehouse_coords = (warehouse['Широта'], warehouse['Долгота'])
        closest_station, min_distance = find_closest_station_to_warehouse(routes_rail, warehouse_coords)
        drive_time_hours = min_distance / average_speed_km_h
        G.add_edge(closest_station, warehouse['Название'], weight=drive_time_hours)

    return G

# Основная функция
def main(file_path, source, target):
    routes_rail, routes_sea, warehouses, schedule = load_data(file_path)
    G = build_graph(routes_rail, routes_sea, warehouses, schedule)
    path_details, length = find_shortest_path(G, source, target)
    if path_details:
        print(f"Кратчайший путь из {source} в {target} занимает {length} часов.")
        for segment in path_details:
            print(f"От {segment[0]} до {segment[1]}, рейс {segment[2]}, дата прибытия {segment[3]}.")
    else:
        print(f"Маршрут из {source} в {target} не найден.")

# Пример использования
file_path = '/Users/evadavydova/Desktop/Реестр.xlsx'
source = 'Шанхай'
target= 'Москва'
main(file_path, source, target)
