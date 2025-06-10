# env/board.py

import random
from dataclasses import dataclass, field
from distutils.core import setup_keywords
from typing import Dict, Optional, Set, List, Tuple
import re

from flask import jsonify

from env.round_manager import RoundManager
from env.config import TILE_STORE
from utils.load_tile_stack import load_tile_stack
from . import round_manager
from .meeple import Meeple, MEEPLE_EXCLUSIVE
from .player import Player
from .round_report import RoundReport, Event
from .tile import Tile, Feature, RoadFeature, CityFeature, CloisterFeature, GardenFeature

# 定义一个二维坐标类型 (x, y)
Coord = Tuple[int, int]
edge_mapping = {
    0: ((0, -1), 5),
    1: ((0, -1), 4),
    2: ((1, 0), 7),
    3: ((1, 0), 6),
    4: ((0, 1), 1),
    5: ((0, 1), 0),
    6: ((-1, 0), 3),
    7: ((-1, 0), 2),
}
# 上下左右四个方向，用于查找相邻位置
DIRECTIONS = [
    (0, -1),  # 上
    (1, 0),  # 右
    (0, 1),  # 下
    (-1, 0),  # 左
]

WHOLE_DIRECTIONS = [
    (-1, -1), (0, -1), (1, -1),
    (-1,  0),          (1,  0),
    (-1,  1), (0,  1), (1,  1)
]


@dataclass
class FeatureGroup:
    """
    🌐 表示一个全局 Feature（特征连通块）
    包含所有连接的 tile 边 + 所有放置的 meeple。
    用于合并判断、闭合判断、计分等。
    """
    tiles: Dict[Tuple[int, int], List[int]]  # 所有属于这个 meta feature 的坐标与边
    meeples: List[Meeple]  # 所有放置在该 feature 上的 meeple
    open_edges: List[Tuple[Tuple[int, int], int]] = field(default_factory=list)
    tags: Set[str] = field(default_factory=set)


@dataclass
class GameBoard:
    """
    🎮 游戏主控制器，管理 tile 放置、特征合并、Meeple 操作、计分、状态报告等。
    持有地图、玩家、牌堆、meta_features 等核心数据。
    """

    def __init__(self, player_num: int = 2, ):

        # 当前地图上已放置的所有 tile，key 是坐标 (x, y)，value 是 Tile 实例
        self.board: Dict[Coord, Tile] = {}

        # 牌堆：游戏开始时加载的全部 tile 列表
        self.stack: list[Tile] = []

        # 空位池：记录地图上所有可以放置 tile 的空位置
        # 每个空位是一个 dict，记录哪些方向有邻居，以及邻居的 feature 类型
        self.empty: Dict[Coord, str] = {}

        self.featureOrderRecorder: Dict[str, Set[Coord]] = {}
        self.current_tile = None
        self.meta_features: Dict[str, Dict[int, FeatureGroup]] = {
            "RoadFeature": {},
            "CityFeature": {},
            "FieldFeature": {},
            "CloisterFeature": {}
        }
        self.players = []
        self.init_players(player_num)
        self.round_manager = round_manager.RoundManager(self.players)

    def restart(self, player_num: int = 2, tile_path: str = TILE_STORE):
        self.board.clear()
        self.stack.clear()
        self.empty.clear()
        self.featureOrderRecorder.clear()
        self.meta_features = {
            "RoadFeature": {},
            "CityFeature": {},
            "FieldFeature": {},
            "CloisterFeature": {}
        }
        self.players.clear()
        self.init_players(player_num)
        self.round_manager = RoundManager(self.players)

        self.load_stack_from_file(tile_path)

        if self.stack:
            self.get_init_tile_and_place_by_id(1747541545336)

    def init_players(self, player_num: int):
        colors = ["red", "blue", "green", "yellow", "purple"]
        self.players = []

        for i in range(player_num):
            name = f"player{i}"
            color = colors[i % len(colors)]
            self.players.append(Player(name, color))

    def load_stack_from_file(self, path: str):
        """
        从本地 JSON 文件中加载 tile 数据，并转换为 Tile 实例列表，存入 stack。
        :param path: JSON 文件路径
        """
        self.stack = load_tile_stack(path)
        print(f"✅ 成功加载 {len(self.stack)} 张 tile")

    def shuffle_stack(self):
        """
        随机打乱牌堆 stack 中的 tile 顺序。
        """
        random.shuffle(self.stack)

    def draw_tile(self):
        self.round_manager.round_report.reset()
        if not self.stack:
            self.current_tile = None
            return None
        self.current_tile = self.stack.pop(0)
        return self.current_tile

    def get_tile_by_id(self, id: int) -> Optional[Tile]:
        for i, tile in enumerate(self.stack):
            if tile.id == id:
                self.current_tile = self.stack.pop(i)
                return self.current_tile
        return None

    def analyze_and_add_feature_tags(self, tile: Tile, coord: Coord) -> None:
        for feature in tile.features:
            feature_type = feature.type
            feature_id = feature.id
            if feature_id == -1:
                continue  # 尚未赋 id 的特征跳过

            meta = self.meta_features[feature_type][feature_id]

            # ✅ 判断道路有客栈
            if isinstance(feature, RoadFeature) and feature.hasInn:
                meta.tags.add("hasInn")

            # ✅ 判断城市有盾牌
            if isinstance(feature, CityFeature) and feature.hasShield:
                meta.tags.add("hasShield")



            # ✅ 你可以扩展更多...

    def simplify_tile_feature_by_rotate(self, tile: Tile, rotate: int):
        """
        对 Tile 进行旋转归一化，直接修改其每个 feature 的 connectedEdges。
        归一化后的 feature.connectedEdges 都是实际摆放后的方向，不再依赖 tile.rotation。
        """

        print(f"\n🌐 开始归一化 Tile ID: {tile.id}，归一化旋转角度: {rotate * 90}°")

        for feature in tile.features:
            original_edges = feature.connectedEdges.copy()
            if feature.type in ["CityFeature", "FieldFeature"]:
                feature.connectedEdges = [(edge + rotate * 2) % 8 for edge in feature.connectedEdges]
            elif feature.type == "RoadFeature":
                feature.connectedEdges = [(edge + rotate) % 4 for edge in feature.connectedEdges]

            print(f"🔧 Feature: {feature.type}")
            print(f"  原始 edges: {original_edges}")
            print(f"  归一化后 edges: {feature.connectedEdges}")

    def place_tile(self, x: int, y: int, rotate: int, tile: Tile, feature_id: Optional[int],
                   meeple_type: Optional[str], frontend_coord: Optional[tuple[int, int]]) -> None:
        """
        将一张 tile 放到地图上的指定坐标处，并可选放置一个 meeple。
        """
        if (x, y) in self.board:
            raise ValueError(f"❌ 位置 ({x}, {y}) 已有 tile，无法再次放置")

        tile.rotation = (-1 * rotate + 4) % 4
        is_put = feature_id is not None
        temp_coord = (x, y)
        self.board[temp_coord] = tile

        print("🧩 放置 Tile：")
        print(f"  ➤ Tile ID: {tile.id}")
        print(f"  ➤ 坐标: ({x}, {y})")
        print(f"  ➤ 旋转角度: {tile.rotation * 90}°")
        self.round_manager.round_report.add_event(Event(
            type="TilePlaced",
            payload={
                "coord": [x, y],
                "tile_id": tile.id,
                "rotation": tile.rotation
            }
        ))
        # self.simplify_tile_feature_by_rotate(tile, rotate)
        self.update_empty_after_placement(x, y, tile)
        self.get_feature_connected_after_placement((x, y))
        self.process_after_placement((x,y))
        self.analyze_and_add_feature_tags(tile, (x, y))


        if feature_id is not None:
            player = self.round_manager.get_current_player()
            meeple = player.get_available_meeple_by_type(meeple_type)
            self.place_meeple(temp_coord, feature_id, meeple, frontend_coord)
            if is_put and meeple:
                print(f"🤺 玩家 {player.name} 选择在 feature #{feature_id} 放置 meeple（类型: {meeple_type}）")
            elif is_put:
                print(f"⚠️ 玩家 {player.name} 想放 meeple（类型: {meeple_type}），但没有可用的")
            else:
                print("📭 本回合未放置 meeple")

        print("\n🗺 当前 Feature 总览：")
        for feature_type, features in self.meta_features.items():
            print(f"📦 {feature_type}:")
            for fid, fg in features.items():
                print(f"  🔹 Feature ID: {fid}")
                for f_coord, edges in fg.tiles.items():
                    edge_list = ', '.join(map(str, edges))
                    print(f"    └─ Tile @ {f_coord}, 边: [{edge_list}]")
                if fg.meeples:
                    for m in fg.meeples:
                        print(f"    👤 Meeple by {m.owner} (type={m.type}, id={m.id})")
                else:
                    print("    💤 没有 meeple 放置在该 feature 上")

    def place_meeple(self, coord: Coord, feature_id: int, meeple: Optional[Meeple],
                     frontend_coord: tuple[int, int]) -> None:
        """
        将 meeple 放置到指定 feature 上，并激活该 meeple。
        """
        print("\n================== [place_meeple 开始执行] ==================")
        print(f"📌 传入参数: coord={coord}, feature_id={feature_id}, meeple={meeple}, frontend_coord={frontend_coord}")

        if meeple is None:
            print("⚠️ 无可用 meeple，跳过放置")
            print("================== [place_meeple 结束：无 meeple] ==================\n")
            return

        tile = self.get_tile_by_coord(*coord)
        if tile is None:
            print(f"❌ 未找到坐标 {coord} 上的 tile，无法放置 meeple")
            print("================== [place_meeple 结束：无 tile] ==================\n")
            return

        # 取到 tile 后，立刻打出其 features 列表：
        print(f"🧮 tile.features = {[{'id': f.id, 'type': f.type, 'edges': f.connectedEdges} for f in tile.features]}")

        # 打印当前 tile 内的所有 feature id 方便排查
        print(f"🗺 Tile @ {coord} 上的所有 feature id 列表: {[f.id for f in tile.features]}")

        found = False
        for f in tile.features:
            print(f"🔍 检查 feature: {f.type}#{f.id}")
            if f.id == feature_id:
                found = True
                print("✅ 找到匹配的 feature，准备放置")

                if not hasattr(f, "meeples"):
                    f.meeples = []
                    print(f"📦 初始化 feature {f.type}#{f.id} 的 meeples 列表")

                f.meeples.append(meeple)
                print(f"➕ 成功加入 tile.features 里的 meeples 列表, 当前数量: {len(f.meeples)}")

                meeple.active = True
                meeple.feature_id = feature_id
                meeple.frontend_coord = frontend_coord

                if f.type in self.meta_features and feature_id in self.meta_features[f.type]:
                    self.meta_features[f.type][feature_id].meeples.append(meeple)
                    print(
                        f"🎯 成功纳入 meta_features[{f.type}][{feature_id}] 列表, 当前数量: {len(self.meta_features[f.type][feature_id].meeples)}")
                    print(
                        f"🎯 完整信息：{self.meta_features[f.type][feature_id].__dict__}")

                    self.round_manager.round_report.add_event(Event(
                        type="MeeplePlaced",
                        payload={
                            "coord": coord,
                            "feature_type": f.type,
                            "feature_id": feature_id,
                            "meeple_type": meeple.type,
                            "player": meeple.owner,
                            "frontend_coord": frontend_coord
                        }
                    ))
                else:
                    print(f"⚠️ 警告：meta_features 中不存在 {f.type}#{feature_id}，可能是 merge 后 id 变化")
                break

        if not found:
            print(f"❌ 未找到 feature_id={feature_id}，在 tile.features 中完全找不到！")

        print("================== [place_meeple 执行结束] ==================\n")

    def get_tile_by_coord(self, x: int, y: int) -> Optional[Tile]:
        """
        获取地图上某个位置的 tile。
        :param x: 横坐标
        :param y: 纵坐标
        :return: 对应位置的 Tile 实例，若该位置为空则返回 None。
        """
        if self.board.get((x, y)):
            return self.board.get((x, y))
        return self.board.get((x, y), None)

    def get_all_coords(self) -> Set[Coord]:
        """
        获取所有已放置 tile 的坐标集合。
        :return: Set of (x, y)
        """
        return set(self.board.keys())

    def get_empty_adjacent_coords(self) -> Set[Coord]:
        """
        获取所有当前地图上可放置 tile 的空位置（即与已有 tile 相邻的空格）。
        :return: Set of (x, y) 坐标
        """
        empty_slots = set()

        for (x, y) in self.board:
            for dx, dy in DIRECTIONS:
                nx, ny = x + dx, y + dy
                if (nx, ny) not in self.board:
                    empty_slots.add((nx, ny))

        return empty_slots

    def get_empty_tile_condition(self, x: int, y: int):
        detail = ['*'] * 4

        if (x, y - 1) in self.board:
            tile = self.board[(x, y - 1)]
            f_type = tile.get_feature_by_edge(4)
            if f_type:
                detail[0] = f_type

        if (x + 1, y) in self.board:
            tile = self.board[(x + 1, y)]
            f_type = tile.get_feature_by_edge(6)
            if f_type:
                detail[1] = f_type

        if (x, y + 1) in self.board:
            tile = self.board[(x, y + 1)]
            f_type = tile.get_feature_by_edge(0)
            if f_type:
                detail[2] = f_type

        if (x - 1, y) in self.board:
            tile = self.board[(x - 1, y)]
            f_type = tile.get_feature_by_edge(2)
            if f_type:
                detail[3] = f_type

        return detail

    def update_empty_after_placement(self, x: int, y: int, tile: Tile):
        if self.empty.get((x, y)):
            old_str = self.empty.pop((x, y))
            if old_str in self.featureOrderRecorder:
                self.featureOrderRecorder[old_str].discard((x, y))

        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy

            if self.board.get((nx, ny)):
                continue

            order = self.get_empty_tile_condition(nx, ny)
            order_str = '|'.join(order)

            if self.empty.get((nx, ny)):
                old_order = self.empty[(nx, ny)]
                if self.featureOrderRecorder.get(old_order):
                    self.featureOrderRecorder[old_order].discard((nx, ny))

            self.empty[(nx, ny)] = order_str

            if not self.featureOrderRecorder.get(order_str):
                self.featureOrderRecorder[order_str] = set()

            self.featureOrderRecorder[order_str].add((nx, ny))


    def get_init_tile(self):
        """
        从牌堆中抽一张 tile 作为起始板块，放在地图中央 (0, 0)。
        :return: 放置的起始 Tile 实例
        """
        if not self.stack:
            raise ValueError("牌堆为空，无法抽取起始 tile")

        init_tile = self.draw_tile()
        self.place_tile(0, 0, 0, init_tile, None, None)
        self.update_empty_after_placement(0, 0, init_tile)  # 如果你实现了这个函数的话
        return init_tile

    def get_init_tile_and_place_by_id(self, tile_id: int) -> Tile:
        """
        指定起始 tile ID，从 stack 中找到对应 tile 并作为起始 tile 放置在 (0, 0)。
        若找到则放入 board，并更新 empty 区域。
        """
        for i, tile in enumerate(self.stack):
            if str(tile.id) == str(tile_id):
                init_tile = self.stack.pop(i)
                self.place_tile(0, 0, 0, init_tile, None, None, None)
                self.update_empty_after_placement(0, 0, init_tile)
                return init_tile

        raise ValueError(f"在牌堆中未找到指定 ID = {tile_id} 的 tile")

    """
    这个函数的目的是，给定一个tile，输出他的边缘序列的str格式，join起来
    @:param tile

    """

    def get_order_str(self, tile: Tile) -> str:
        str_order = {}
        for feature in tile.features:
            if feature.type == "FieldFeature":
                for n in feature.connectedEdges:
                    str_order[int(n / 2)] = "FieldFeature"
            if feature.type == "CityFeature":
                for n in feature.connectedEdges:
                    str_order[int(n / 2)] = "CityFeature"
            if feature.type == "RoadFeature":
                for n in feature.connectedEdges:
                    str_order[int(n)] = "RoadFeature"
        return '|'.join([str_order.get(i, '*') for i in range(4)])

    def get_pattern(self, key: str) -> str:
        # 把 * 替换为能匹配任意一段内容（非竖线）
        return re.escape(key).replace(r'\*', r'[^|]*')

    def get_all_suitable_positions(self, tile: Tile, is_add_meeple) -> list[dict]:
        all_placements = []
        seen = set()
        raw_order = self.get_order_str(tile)
        extended = raw_order + "|" + raw_order
        pipe_positions = [m.start() for m in re.finditer(r'\|', extended)]

        for i in range(4):
            if i == 0:
                substr = extended[:pipe_positions[3]]
            else:
                substr = extended[pipe_positions[i - 1] + 1:pipe_positions[i + 3]]

            rotation = i
            for key, coords in self.featureOrderRecorder.items():
                pattern = re.compile(re.escape(key).replace(r'\*', r'[^|]*') + r'$')
                if pattern.fullmatch(substr):
                    for coord in coords:
                        if (coord, rotation) in seen:
                            continue

                        seen.add((coord, rotation))

                        # ✅ 不需要 meeple 情况下，直接返回坐标 + 旋转
                        if not is_add_meeple:
                            all_placements.append({
                                "coord": coord,
                                "rotation": rotation
                            })
                            continue

                        # 🔁 需要 meeple 时，才调用 meeple 逻辑
                        meeple_options = self.get_meeple_placement_condition(
                            tile, coord, rotation, self.round_manager.get_current_player()
                        )

                        # 🔍 打印调试信息
                        print(f"🧩 在位置 {coord}，旋转 {rotation * 90}° 可放置 meeple 的选项如下：")
                        if meeple_options:
                            for idx, option in enumerate(meeple_options, 1):
                                if option.get("is_put"):
                                    print(f"  [{idx}] ✅ 可放置 Meeple")
                                    print(f"     FeatureType: {option['featureType']}")
                                    print(f"     FeatureID: {option['featureId']}")
                                    print(f"     MeepleType: {option['meepleType']}")
                                    print(f"     Coord: {option['coord']}")
                                    print(f"     Rotation: {option['rotation'] * 90}°")
                                    print(f"     FrontendCoord: {option['frontend_coord']}")
                                else:
                                    print(f"  [{idx}] 🚫 不可放置 Meeple")
                                    print(f"     FeatureType: {option['featureType']}")
                                    print(f"     FeatureID: {option['featureId']}")
                                    print(f"     Coord: {option['coord']}")
                                    print(f"     Rotation: {option['rotation'] * 90}°")
                        else:
                            print("  ❌ 没有合法的 meeple 放置方式。")

                        # 📌 加入所有返回的 option（注意不是 coord，而是含详细信息的 dict）
                        all_placements.extend(meeple_options)

        return all_placements

    def print_board(self):
        """
        打印当前地图的可视化布局（控制台文本模式）。
        放置了 tile 的格子用 🟩 显示，空位用 ⬜ 显示。
        """
        coords = self.get_all_coords()
        if not coords:
            print("Board is empty.")
            return

        xs, ys = zip(*coords)
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        for y in range(min_y, max_y + 1):
            row = ""
            for x in range(min_x, max_x + 1):
                if (x, y) in self.board:
                    row += "🟩 "
                else:
                    row += "⬜ "
            print(row)

    # 此代码是在等待放置完后才用的，而且要用在place内部，外部不要随便调用

    def get_feature_id_by_coord_and_edge(self, coord: Coord, edge: int, feature_name: str) -> int:
        temp_tile = self.get_tile_by_coord(coord[0], coord[1])
        for feature in temp_tile.features:
            if feature.type == feature_name:
                for n in feature.connectedEdges:
                    if n == edge:
                        if not feature.id:
                            feature.id = -1
                        return feature.id
        return -1

    def merge_feature_ids(self, feature_type: str, from_id: int, to_id: int):
        if from_id == to_id:
            return

        from_group = self.meta_features[feature_type][from_id].tiles
        to_group = self.meta_features[feature_type][to_id].tiles
        coords = set()
        for coord, edges in from_group.items():
            # 合并到目标 group
            to_group[coord] = edges
            coords.add(coord)

        for coord in coords:
            for feature in self.board[coord].features:
                if feature.type == feature_type and feature.id == from_id:
                    feature.id = to_id
        # 删除原来的 group
        del self.meta_features[feature_type][from_id]

    """
    这个函数是两种可能的
    一种是，已经放置了，然后去获取该格子上有没有meeple
    一种是，还没有放置，这个坐标是空的，然后去获取这个格子的meeple放置可能性
    """

    # 这个函数是新的写法，上面的是获取综合的meeple摆放方式，现在我不用这么复杂的，我只要在一个位置一个rot下获取一定的就可以了
    def get_meeple_options_for_position(self, tile: Tile, coord: Coord, rotation: int, player: Player):
        x, y = coord
        result = []

        # 获取玩家当前未使用的 meeple 类型
        available_meeple_types = [m.type for m in player.meeples if not m.active]

        for i, feature in enumerate(tile.features):
            if feature.type not in ["RoadFeature", "CityFeature", "FieldFeature"]:
                continue  # 只处理三类 feature

            is_occupied = False
            owner_occupied = False

            # 先判断自己 feature 里的 meeple
            meeples = self.meta_features[feature.type][feature.id].meeples
            for m in meeples:
                if m.type in ["big", "normal"]:
                    is_occupied = True
                if m.owner == player.name:  # 👈 注意：这里 owner 应该是名字
                    owner_occupied = True

            # 如果 feature 本身未被完全占用，还需要检查邻居
            if not is_occupied:
                for edge in feature.connectedEdges:
                    if edge_mapping.get(edge):
                        temp_coord, temp_edge = edge_mapping[edge]
                        neighbor = self.get_tile_by_coord(temp_coord[0] + x, temp_coord[1] + y)
                        if neighbor:
                            for temp_f in neighbor.features:
                                if temp_f.type != feature.type:
                                    continue
                                edge_to_check = int(temp_edge / 2) if feature.type == "RoadFeature" else temp_edge
                                if edge_to_check in temp_f.connectedEdges:
                                    temp_meta_f = self.meta_features[feature.type].get(temp_f.id)
                                    if temp_meta_f:
                                        for meeple in temp_meta_f.meeples:
                                            if meeple.type in ["big", "normal"]:
                                                is_occupied = True
                                                break
                                if is_occupied:
                                    break
                    if is_occupied:
                        break

            # 计算前端位置 (为了防止贴边贴死，进行了一点偏移)
            frontend_coord = tile.get_meeple_proper_position(feature, rotation)
            fx, fy = frontend_coord
            fx = 10 if fx == 0 else 90 if fx == 100 else fx
            fy = 10 if fy == 0 else 90 if fy == 100 else fy
            frontend_coord = (fx, fy)

            # 如果没有被占用，可以放互斥型 meeple
            if not is_occupied:
                for meeple_class in ["normal", "big"]:
                    if meeple_class in available_meeple_types:
                        result.append({
                            "coord": [x, y],
                            "rotation": rotation,
                            "featureType": feature.type,
                            "featureId": feature.id,
                            "frontend_coord": frontend_coord,
                            "meepleType": meeple_class
                        })
            else:
                # 如果已经被占用，但自己曾经在上面放过，且有 builder 可以放 builder
                if owner_occupied and "builder" in available_meeple_types:
                    result.append({
                        "coord": [x, y],
                        "rotation": rotation,
                        "featureType": feature.type,
                        "featureId": feature.id,
                        "frontend_coord": frontend_coord,
                        "meepleType": "builder"
                    })

        return result

    def get_feature_connected_after_placement(self, coord: Coord):
        tile = self.get_tile_by_coord(coord[0], coord[1])
        rotate = tile.rotation

        for feature in tile.features:
            ids = set()
            print("\n=================【处理新放置的 Feature】=================")
            print(f"🧩 Feature类型: {feature.type} | 边: {feature.connectedEdges} | Tile旋转角度: {rotate}")

            if feature.type == "RoadFeature":
                # RoadFeature：使用 4 边逻辑，边编号映射到 8 边坐标系（*2）
                for edge in feature.connectedEdges:
                    rotated_edge = int((edge * 2 + rotate) % 8)
                    print(
                        f"➡️ RoadFeature: 原始边 {edge} 经过旋转 {rotate * 90}° 后，计算得到 rotated_edge={rotated_edge}")

                    if rotated_edge not in edge_mapping:
                        print(f"⚠️ rotated_edge {rotated_edge} 没有在 edge_mapping 中，跳过")
                        continue

                    (dx, dy), neighbor_edge = edge_mapping[rotated_edge]
                    neighbor_coord = (coord[0] + dx, coord[1] + dy)
                    print(f"➡️ 寻找邻居坐标: {neighbor_coord}，邻居期望边: {neighbor_edge}")

                    neighbor_tile = self.get_tile_by_coord(*neighbor_coord)
                    if neighbor_tile:
                        print(f"✅ 找到邻居 Tile @ {neighbor_coord}，邻居 Tile 旋转角度: {neighbor_tile.rotation}")

                        for nf in neighbor_tile.features:
                            if nf.type != feature.type:
                                continue

                            # 计算邻居的实际边（注意邻居自身也有旋转角度！）
                            rotated_neighbor_edges = [(e + neighbor_tile.rotation) % 4 for e in nf.connectedEdges]
                            print(
                                f"  ➡️ 邻居 Feature (Road) ID={nf.id}，邻居边={nf.connectedEdges} → 实际边={rotated_neighbor_edges}")

                            if int(neighbor_edge / 2) in rotated_neighbor_edges and nf.id != -1:
                                print(f"  ✅ 邻居匹配成功！邻居 feature ID={nf.id}")
                                ids.add(nf.id)
                    else:
                        print(f"❌ 邻居 Tile @ {neighbor_coord} 不存在，跳过")

            elif feature.type in ("CityFeature", "FieldFeature"):
                for edge in feature.connectedEdges:
                    rotated_edge = (edge + rotate * 2) % 8
                    print(
                        f"➡️ {feature.type}: 原始边 {edge} 经过旋转 {rotate * 90}° 后，计算得到 rotated_edge={rotated_edge}")

                    if rotated_edge not in edge_mapping:
                        print(f"⚠️ rotated_edge {rotated_edge} 没有在 edge_mapping 中，跳过")
                        continue

                    (dx, dy), neighbor_base_edge = edge_mapping[rotated_edge]
                    neighbor_coord = (coord[0] + dx, coord[1] + dy)
                    print(f"➡️ 寻找邻居坐标: {neighbor_coord}，邻居期望边: {neighbor_base_edge}")

                    neighbor_tile = self.get_tile_by_coord(*neighbor_coord)
                    if neighbor_tile:
                        print(f"✅ 找到邻居 Tile @ {neighbor_coord}，邻居 Tile 旋转角度: {neighbor_tile.rotation}")

                        for nf in neighbor_tile.features:
                            if nf.type != feature.type:
                                continue

                            rotated_neighbor_edges = [(e + neighbor_tile.rotation * 2) % 8 for e in nf.connectedEdges]
                            print(
                                f"  ➡️ 邻居 Feature (City/Field) ID={nf.id}，邻居边={nf.connectedEdges} → 实际边={rotated_neighbor_edges}")

                            if neighbor_base_edge in rotated_neighbor_edges and nf.id != -1:
                                print(f"  ✅ 邻居匹配成功！邻居 feature ID={nf.id}")
                                ids.add(nf.id)
                    else:
                        print(f"❌ 邻居 Tile @ {neighbor_coord} 不存在，跳过")

            print(f"🔗 完成 {feature.type} 邻居搜索，找到 IDs: {ids}")

            if len(ids) == 0:
                new_id = len(self.meta_features[feature.type])
                new_edges = {coord: feature.connectedEdges.copy()}
                fg = FeatureGroup(new_edges, [])
                self.meta_features[feature.type][new_id] = fg
                feature.id = new_id
                print(f"🆕 新建 {feature.type}，分配 ID: {new_id}")

            elif len(ids) == 1:
                new_id = ids.pop()
                self.meta_features[feature.type][new_id].tiles[coord] = feature.connectedEdges.copy()
                feature.id = new_id
                print(f"✅ 继承 {feature.type}，复用已有 ID: {new_id}")

            else:
                min_id = min(ids)
                print(f"⚠️ 需要合并 {feature.type} IDs: {ids} → 合并到 ID {min_id}")
                for fid in ids:
                    self.merge_feature_ids(feature.type, fid, min_id)
                feature.id = min_id

            all_ids = list(self.meta_features[feature.type].keys())
            print(f"📊 当前 {feature.type} 全部 IDs: {all_ids}")
            print("========================================================\n")

    def scoring_feature(self, feature_id: int, feature_type: str):
        if feature_type == "RoadFeature":
            score = 1 * len(self.meta_features[feature_type][feature_id].tiles)
            return score
        if feature_type == "CityFeature":
            score = 2 * len(self.meta_features[feature_type][feature_id].tiles)
            return score

    def get_current_state(self, coord: Coord):
        round_report = RoundReport()
        tile = self.current_tile or self.get_tile_by_coord(coord[0], coord[1])

        if tile is None:
            return None
        for feature in tile.features:
            meta_f = self.meta_features[feature.type][feature.id]
            count = 0
            for e in meta_f.tiles.values():
                count += len(e)
            if count % 2 == 0:
                pass

    #             触发计分

    def get_map_data(self):
        result = []
        for (x, y), tile in self.board.items():
            tile_data = {
                "x": x,
                "y": y,
                "id": tile.id,
                "rotation": tile.rotation,
                "meeples": []
            }

            for feature in tile.features:
                for meeple in feature.meeples:
                    if meeple.active:
                        tile_data["meeples"].append({
                            "featureId": feature.id,
                            "featureType": feature.type,
                            "meepleType": meeple.type,
                            "owner": meeple.owner,
                            "frontendCoord": meeple.frontend_coord
                        })

            result.append(tile_data)
        return result

    def assign_real_id_before_placement(self, coord: Coord, rotate: int, feature: Feature):
        ids = set()
        x, y = coord
        is_road = feature.type == "RoadFeature"

        for edge in feature.connectedEdges:
            if is_road:
                rotated_edge = int((edge + rotate) % 4 * 2)
            else:
                rotated_edge = (edge + rotate * 2) % 8

            if rotated_edge in edge_mapping:
                (dx, dy), neighbor_edge = edge_mapping[rotated_edge]
                nx, ny = x + dx, y + dy
                neighbor_tile = self.get_tile_by_coord(nx, ny)

                if not neighbor_tile:
                    continue

                expected_edge = int(neighbor_edge / 2) if is_road else neighbor_edge

                for nf in neighbor_tile.features:
                    if nf.type != feature.type:
                        continue
                    if expected_edge in nf.connectedEdges and nf.id != -1:
                        ids.add(nf.id)

        # 分配 ID
        if len(ids) == 0:

            return len(self.meta_features[feature.type])
        else:
            return min(ids)

    def process_after_placement(self, coord: Coord):
        tile = self.current_tile or self.get_tile_by_coord(coord[0], coord[1])
        if tile is None:
            return
        # 这里要加一个去除相邻的clo的空边
        for feature in tile.features:
            fg = self.meta_features[feature.type][feature.id]
            if feature.type == "CloisterFeature":
                for nx, ny in WHOLE_DIRECTIONS:
                    if self.board.get((nx, ny)) is None:
                        fg.open_edges.append(((nx, ny), -1))
                continue
            #     如果是需要多个板块完成的feature，那就需要在下面去进行一个处理，首先是，对所有新的相邻边来一手append
            for edge in feature.connectedEdges:

                if feature.type == "RoadFeature":
                    rotated_edge = (edge + tile.rotation) % 4  # RoadFeature 边是偶数位（0,2,4,6）
                elif feature.type == "CityFeature" :
                    rotated_edge = (edge + tile.rotation * 2) % 8

                else:
                    continue  # 忽略不需要处理的 Feature 类型
                if (coord,rotated_edge) in fg.open_edges:
                    fg.open_edges.remove((coord,rotated_edge))
                if rotated_edge not in edge_mapping:
                    continue

                (dx, dy), neighbor_edge = edge_mapping[rotated_edge]
                nx, ny = coord[0] + dx, coord[1] + dy
                neighbor = self.get_tile_by_coord(nx, ny)

                if neighbor is None:
                    fg.open_edges.append(((coord[0], coord[1]), neighbor_edge))




    def scoring(self, coord: Coord):
        tile = self.current_tile or self.get_tile_by_coord(coord[0], coord[1])
        if tile is None:
            return "no tile found"
        score_result = []
        for feature in tile.features:
            if feature.type == "RoadFeature" and len(self.meta_features[feature.type][feature.id].open_edges) == 0 :
                print("开始计算分数")
                fg = self.meta_features[feature.type][feature.id]
                for coord,edges in fg.tiles.items():
                    tile = self.get_tile_by_coord(coord[0], coord[1])
                    for f in tile.features:
                        if f.id == feature.id and :

                score_result.append()























