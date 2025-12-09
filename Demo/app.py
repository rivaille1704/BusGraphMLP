from flask import Flask, request, jsonify
from flask_cors import CORS
import pickle
import networkx as nx
import math
import heapq

app = Flask(__name__)
CORS(app)
GRAPH_FILE = "hanoi_graph_schedule.pkl"

print(f"⏳ Loading graph...")
try:
    with open(GRAPH_FILE, "rb") as f:
        G = pickle.load(f)
    print(f"Graph loaded: {len(G.nodes)} nodes, {len(G.edges)} edges.")
except Exception as e:
    print(f"Error: {e}")
    exit(1)

def get_k_nearest(lat, lon, k=3):
    cands = []
    for n, d in G.nodes(data=True):
        if 'lat' in d:
            dist = math.sqrt((d['lat']-lat)**2 + (d['lon']-lon)**2) * 111000
            cands.append((n, dist))
    cands.sort(key=lambda x: x[1])
    return cands[:k]

def time_to_str(t):
    h = int(t) % 24
    m = int((t - int(t)) * 60)
    return f"{h:02d}:{m:02d}"

# THUẬT TOÁN DIJKSTRA PHỤ THUỘC THỜI GIAN
def find_path_time_dependent(start_node, end_node, start_time):
    pq = [(start_time, start_node)]
    parent = {start_node: None}
    min_arrival = {start_node: start_time}
    final_arrival = float('inf')
    
    while pq:
        curr_time, u = heapq.heappop(pq)
        
        if curr_time > min_arrival.get(u, float('inf')): continue
        if u == end_node:
            final_arrival = curr_time
            break
            
        for v, data in G[u].items():
            etype = data.get('type', 'bus')
            travel_t = data.get('base_travel_time', 5) / 60.0
            
            hour_of_day = curr_time % 24
            is_rush = (7 <= hour_of_day <= 9) or (17 <= hour_of_day <= 19)
            if etype == 'bus' and is_rush: travel_t *= 2.0
            
            departure_t = curr_time
            wait_t = 0
            
            if etype == 'bus':
                schedule = data.get('schedule')
                if not schedule: continue
                found_trip = False
                for trip_t in schedule:
                    if trip_t >= curr_time:
                        departure_t = trip_t
                        wait_t = trip_t - curr_time
                        found_trip = True
                        break
                if not found_trip: continue
            
            arrival_t = departure_t + travel_t
            
            if arrival_t < min_arrival.get(v, float('inf')):
                min_arrival[v] = arrival_t
                parent[v] = {
                    'u': u, 'type': etype, 'route': data.get('route_id'),
                    'dept': departure_t, 'arr': arrival_t, 'wait': wait_t
                }
                heapq.heappush(pq, (arrival_t, v))
                
    if end_node not in parent or parent[end_node] is None:
        return None, float('inf')
        
    path = []
    curr = end_node
    while curr != start_node:
        info = parent[curr]
        path.append({
            'u': info['u'], 'v': curr,
            'type': info['type'], 'route': info['route'],
            'dept': info['dept'], 'arr': info['arr'], 'wait': info['wait'] * 60
        })
        curr = info['u']
    
    return path[::-1], final_arrival

@app.route('/get_all_stops', methods=['GET'])
def get_all_stops():
    stops = [{'id': n, 'lat': d['lat'], 'lon': d['lon'], 'name': d.get('stop_name')} 
             for n, d in list(G.nodes(data=True))[:3000] if 'lat' in d]
    return jsonify(stops)

@app.route('/find_route', methods=['POST'])
def find_route():
    try:
        d = request.json
        h, m = map(int, d.get('time', '08:00').split(':'))
        start_t_base = h + m/60.0
        
        starts = get_k_nearest(d['start']['lat'], d['start']['lon'])
        ends = get_k_nearest(d['end']['lat'], d['end']['lon'])
        
        if not starts or not ends: return jsonify({'status': 'error', 'message': 'No stops found'}), 404
        
        best_res = None
        min_global_time = float('inf')
        
        for s_id, s_dist in starts:
            for e_id, e_dist in ends:
                if s_id == e_id: continue
                
                # Đi bộ đầu
                w1_time = (s_dist / 1.3) / 60.0 
                arr_at_start_node = start_t_base + w1_time/60.0
                
                path_segs, arr_at_end_node = find_path_time_dependent(s_id, e_id, arr_at_start_node)
                
                if path_segs:
                    # Đi bộ cuối
                    w2_time = (e_dist / 1.3) / 60.0
                    total_finish = arr_at_end_node + w2_time/60.0
                    
                    if total_finish < min_global_time:
                        min_global_time = total_finish
                        
                        res_segs = []
                        
                        # --- KHỞI TẠO SEGMENT ĐẦU TIÊN ---
                        curr_seg = {
                            'type': 'walk',
                            'route': None,
                            'start_name': "Điểm xuất phát",
                            'end_name': G.nodes[s_id].get('stop_name'),
                            'dist': int(s_dist),
                            'time_mins': w1_time,
                            'coords': [[d['start']['lat'], d['start']['lon']], [G.nodes[s_id]['lat'], G.nodes[s_id]['lon']]],
                            'dept_time': start_t_base,
                            'arr_time': arr_at_start_node
                        }

                        # --- HÀM HỖ TRỢ ĐÓNG GÓI SEGMENT ---
                        def finalize_segment(seg):
                            if seg['type'] == 'walk':
                                css_type = 'transfer'
                                title = f"Chuyển tuyến tại {seg['start_name']}"
                                
                                if seg['start_name'] == "Điểm xuất phát":
                                    title = "Xuất phát"
                                    css_type = 'walk'
                                elif seg['end_name'] == "Điểm đến":
                                    title = "Về đích"
                                    css_type = 'walk'
                                
                                sub = f"Đi bộ đến <b>{seg['end_name']}</b> trong {int(seg['time_mins'])} phút"
                                return {'type': css_type, 'desc': title, 'sub': sub, 'coords': seg['coords']}
                            else:
                                title = f"Xe buýt {seg['route']}"
                                sub = f"Lên lúc {time_to_str(seg['dept_time'])} • Xuống lúc {time_to_str(seg['arr_time'])} tại <b>{seg['end_name']}</b>"
                                return {'type': 'bus', 'desc': title, 'sub': sub, 'coords': seg['coords']}
                        for seg in path_segs:
                            u_node, v_node = G.nodes[seg['u']], G.nodes[seg['v']]
                            coord_v = [v_node['lat'], v_node['lon']]
                            
                            seg_duration = (seg['arr'] - seg['dept']) * 60.0
                            is_walk_edge = (seg['type'] == 'walk')
                            
                            if is_walk_edge:
                                if curr_seg['type'] == 'walk':
                                    curr_seg['dist'] += int(G[seg['u']][seg['v']].get('weight', 0))
                                    curr_seg['time_mins'] += seg_duration
                                    curr_seg['coords'].append(coord_v)
                                    curr_seg['end_name'] = v_node.get('stop_name') # Cập nhật điểm đến cuối cùng
                                    curr_seg['arr_time'] = seg['arr']
                                else:
                                    res_segs.append(finalize_segment(curr_seg))
                                    
                                    curr_seg = {
                                        'type': 'walk',
                                        'route': None,
                                        'start_name': u_node.get('stop_name'),
                                        'end_name': v_node.get('stop_name'),
                                        'dist': int(G[seg['u']][seg['v']].get('weight', 0)),
                                        'time_mins': seg_duration,
                                        'coords': [[u_node['lat'], u_node['lon']], coord_v],
                                        'dept_time': seg['dept'],
                                        'arr_time': seg['arr']
                                    }
                            else: 
                                if curr_seg['type'] == 'bus' and curr_seg['route'] == seg['route']:
                                    curr_seg['coords'].append(coord_v)
                                    curr_seg['end_name'] = v_node.get('stop_name')
                                    curr_seg['arr_time'] = seg['arr']
                                else:
                                    res_segs.append(finalize_segment(curr_seg))
                                    
                                    curr_seg = {
                                        'type': 'bus',
                                        'route': seg['route'],
                                        'start_name': u_node.get('stop_name'),
                                        'end_name': v_node.get('stop_name'),
                                        'coords': [[u_node['lat'], u_node['lon']], coord_v],
                                        'dept_time': seg['dept'],
                                        'arr_time': seg['arr']
                                    }
                        
                        if curr_seg['type'] == 'walk':
                            curr_seg['dist'] += int(e_dist)
                            curr_seg['time_mins'] += w2_time
                            curr_seg['coords'].append([d['end']['lat'], d['end']['lon']])
                            curr_seg['end_name'] = "Điểm đến"
                            curr_seg['arr_time'] = total_finish
                            res_segs.append(finalize_segment(curr_seg))
                        else:                           
                            res_segs.append(finalize_segment(curr_seg))
                            
                            res_segs.append({
                                'type': 'walk',
                                'desc': "Về đích",
                                'sub': f"Đi bộ về đích trong {int(w2_time)} phút (Đến nơi lúc {time_to_str(total_finish)})",
                                'coords': [[G.nodes[e_id]['lat'], G.nodes[e_id]['lon']], [d['end']['lat'], d['end']['lon']]]
                            })
                        
                        best_res = {
                            'total_duration': int((min_global_time - start_t_base)*60),
                            'arrival_time': time_to_str(min_global_time),
                            'segments': res_segs
                        }

        if not best_res:
            return jsonify({'status': 'error', 'message': 'Không tìm thấy đường (có thể hết xe).'}), 404
            
        return jsonify({'status': 'success', **best_res})

    except Exception as e:
        print(e)
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)