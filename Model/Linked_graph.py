import pickle
import networkx as nx
from sklearn.neighbors import BallTree
import numpy as np
import math
import random
import os
import pandas as pd

# CẤU HÌNH
INPUT_GRAPH_FILE = "hanoi_graphs_normal.pkl" # Lấy cấu trúc đồ thị ban đầu
OUTPUT_FILE = "hanoi_graph_schedule.pkl"
STOPS_FILE = "stops.txt"
MAX_WALK_DIST = 300  # Mét
WALK_SPEED = 1.3     # m/s (~4.7 km/h) - Tốc độ đi bộ trung bình

print("Đang tải cấu trúc đồ thị...")
try:
    with open(INPUT_GRAPH_FILE, "rb") as f:
        data_input = pickle.load(f)
    # Lấy đồ thị giờ số 8 làm khung xương
    G_base = data_input.get(8, data_input[list(data_input.keys())[0]]).copy()
except FileNotFoundError:
    print("Không tìm thấy file input")
    G_base = nx.fast_gnp_random_graph(200, 0.05, directed=True)
    for u, v in G_base.edges(): G_base[u][v]['weight'] = random.randint(300, 2000)
    for n in G_base.nodes(): 
        G_base.nodes[n]['lat'] = 21.0 + random.random()*0.1
        G_base.nodes[n]['lon'] = 105.8 + random.random()*0.1

# NẠP TÊN TRẠM----
if os.path.exists(STOPS_FILE):
    print(f"📖 Đọc tên trạm từ {STOPS_FILE}...")
    df_stops = pd.read_csv(STOPS_FILE)
    name_map = dict(zip(df_stops.stop_id, df_stops.stop_name))
    for n in G_base.nodes():
        if n in name_map: G_base.nodes[n]['stop_name'] = name_map[n]
        if 'stop_name' not in G_base.nodes[n]: G_base.nodes[n]['stop_name'] = f"Trạm {n}"
else:
    for n in G_base.nodes():
        if 'stop_name' not in G_base.nodes[n]: G_base.nodes[n]['stop_name'] = f"Trạm {n}"

# GIẢ LẬP LỊCH TRÌNH XE CHẠY (SCHEDULE)
print("Đang tạo lịch trình chạy xe (Schedule Simulation)...")

# Tạo danh sách các tuyến giả định
route_configs = {}

for u, v, d in G_base.edges(data=True):
    # Mặc định là cạnh xe buýt
    d['type'] = 'bus'
    
    # Gán/Tạo Route ID
    if 'route_id' not in d: d['route_id'] = f"{random.randint(1, 40):02d}"
    rid = d['route_id']
    
    # Cấu hình tuyến (nếu chưa có)
    if rid not in route_configs:
        # Random giờ hoạt động: 5h-22h hoặc 5h-20h
        end_h = np.random.choice([20.0, 21.0, 22.0, 22.5], p=[0.1, 0.3, 0.5, 0.1])
        freq_peak = random.choice([0.16, 0.25]) # 10p hoặc 15p
        freq_off = random.choice([0.33, 0.5])   # 20p hoặc 30p
        route_configs[rid] = {'end': end_h, 'fp': freq_peak, 'fo': freq_off}
    
    config = route_configs[rid]
    
    # Sinh lịch trình chạy xe (Departure Times tại trạm u)
    # Giả sử xe chạy từ 5:00 sáng
    schedule = []
    t = 5.0 + random.uniform(0, 0.5) # Random offset
    
    while t <= config['end']:
        schedule.append(t)
        # Giờ cao điểm: 7-9h, 16:30-18:30
        if (7 <= t <= 9) or (16.5 <= t <= 18.5):
            t += config['fp']
        else:
            t += config['fo']
            
    d['schedule'] = sorted(schedule)
    
    # Tính thời gian di chuyển giữa 2 trạm (Travel Time)
    dist_m = d.get('weight', 500)
    # Vận tốc xe buýt: 25km/h (giờ thường), 15km/h (giờ cao điểm - sẽ xử lý ở backend)
    d['base_travel_time'] = (dist_m / (25/3.6)) / 60.0 # Phút

# TẠO CẠNH ĐI BỘ (TRANSFER EDGES)
print("🔗 Đang nối các trạm đi bộ...")
nodes_coords = []
node_ids_list = []

for n, d in G_base.nodes(data=True):
    if 'lat' in d and 'lon' in d:
        nodes_coords.append([math.radians(d['lat']), math.radians(d['lon'])])
        node_ids_list.append(n)

if nodes_coords:
    tree = BallTree(np.array(nodes_coords), metric='haversine')
    # Tìm các trạm trong bán kính MAX_WALK_DIST
    indices = tree.query_radius(nodes_coords, r=MAX_WALK_DIST/6371000)
    
    transfer_edges = []
    count_transfers = 0
    
    for i, neighbors in enumerate(indices):
        u = node_ids_list[i]
        for j in neighbors:
            v = node_ids_list[j]
            if u == v: continue
            
            # Tính khoảng cách thực
            lat1, lon1 = math.radians(G_base.nodes[u]['lat']), math.radians(G_base.nodes[u]['lon'])
            lat2, lon2 = math.radians(G_base.nodes[v]['lat']), math.radians(G_base.nodes[v]['lon'])
            dlon = lon2 - lon1
            dlat = lat2 - lat1
            a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
            c = 2 * math.asin(math.sqrt(a))
            dist_m = c * 6371000
            
            walk_time_min = (dist_m / WALK_SPEED) / 60.0
            
            transfer_edges.append((u, v, {
                'weight': dist_m,
                'base_travel_time': walk_time_min,
                'type': 'walk',
                'route_id': 'WALK',
                'schedule': None # Đi bộ lúc nào cũng được
            }))
            count_transfers += 1
            
    G_base.add_edges_from(transfer_edges)
    print(f"✅ Đã thêm {count_transfers} cạnh đi bộ.")

# LẤY CỤM LIÊN THÔNG & LƯU
if nx.number_weakly_connected_components(G_base) > 1:
    largest_cc = max(nx.weakly_connected_components(G_base), key=len)
    G_final = G_base.subgraph(largest_cc).copy()
    print(f"🧹 Đã lọc cụm liên thông lớn nhất: {len(G_final)} nút.")
else:
    G_final = G_base

with open(OUTPUT_FILE, "wb") as f:
    pickle.dump(G_final, f)

print(f"💾 Đã lưu file '{OUTPUT_FILE}'.")