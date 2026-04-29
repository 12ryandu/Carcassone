from audioop import error
from dataclasses import asdict

from exceptiongroup import catch
from flask import Flask, request, jsonify
from flask_cors import CORS
from env.board import GameBoard, ScoringEvent
import json
import os
from env.config import TILE_STORE

app = Flask(__name__)
CORS(app)

# ✅ 确保 tile 数据文件夹存在
os.makedirs("tile_store", exist_ok=True)

# ✅ 如果 tile 数据文件不存在则初始化空文件
if not os.path.exists(TILE_STORE):
    with open(TILE_STORE, "w") as f:
        json.dump([], f)

# ✅ 实例化主游戏板
board = GameBoard()
board.load_stack_from_file(TILE_STORE)

# ---------------------------------------------
# ✅ Tile 数据管理接口
# ---------------------------------------------

@app.route("/add_tile", methods=["POST"])
def add_tile():
    """
    用于向 tile_store 文件中手动添加 tile（数据录入阶段用）
    """
    try:
        data = request.get_json()
        print("🔍 收到数据：", data)

        with open(TILE_STORE, "r") as f:
            tiles = json.load(f)

        tiles.append(data)

        with open(TILE_STORE, "w") as f:
            json.dump(tiles, f, indent=2)

        return jsonify({"message": "Tile saved!"})
    except Exception as e:
        print("❌ 后端出错：", e)
        return jsonify({"error": str(e)}), 500

# ---------------------------------------------
# ✅ 抽牌逻辑（仅抽取，不进入回合推进）
# ---------------------------------------------

@app.route('/api/draw_tile', methods=['POST'])
def draw_tile():
    """
    仅抽取下一张 tile
    """
    tile = board.draw_tile()
    if tile is None:
        return jsonify({"error": "No more tiles"}), 400

    tile.rotation = 0
    print(f"🎲 当前摸到 tile: {tile.id}")
    return jsonify({"id": tile.id, "rotation": tile.rotation})


# ---------------------------------------------
# ✅ 地图状态查看
# ---------------------------------------------

@app.route("/api/map")
def api_map():
    """
    获取当前地图上所有已放置 tiles
    """
    result = []
    for (x, y), tile in board.board.items():
        result.append({
            "x": x,
            "y": y,
            "id": tile.id,
            "rotation": tile.rotation
        })
    return jsonify(result)


# ---------------------------------------------
# ✅ 未来的状态机控制接口（目前测试用）
# ---------------------------------------------

@app.route("/api/round-manager/what-now", methods=["GET"])
def what_now():
    try:
        rm = board.round_manager

        response = {
            "round": rm.round,
            "phase": rm.get_phase(),
            "currentPlayerIndex": rm.get_current_player_index(),
            "currentPlayer": rm.get_current_player().name
        }
        return jsonify(response), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------
# ✅ 预设地图快速填充接口（测试开发用）
# ---------------------------------------------

@app.route("/api/preset_map", methods=["POST"])
def preset_map():
    """
    加载写死的固定地图布局（便于开发调试用）
    """
    print("📌 收到 preset_map 请求，添加写死地图 tile...")
    board.load_stack_from_file(TILE_STORE)

    layout = [
        ((0, 0), "1747541545336", 0),
        ((0, -1), "1747540282275", 0),
        ((-1, -1), "1747540695979", 0),
        ((0, -2), "1747541544009", 0),
        ((1, 0), "1747542390302", 0),
        ((1, -1), "1747542439724", 2),
        ((2, -1), "1747542514290", 0),
        ((-1, -2), "1747542528610", 2),
    ]

    for (x, y), tile_id, rot in layout:
        if (x, y) in board.board:
            continue
        for i, tile in enumerate(board.stack):
            if str(tile.id) == tile_id:
                board.place_tile(x, y, rot, board.stack.pop(i))
                print(f"✅ 放置 tile: {tile_id} at ({x},{y}) rot={rot}")
                break
        else:
            print(f"❌ tile {tile_id} 不在 stack 中")

    print(f"目前还剩{len(board.stack)}张牌")
    return jsonify({"message": "固定地图已添加"})


# ---------------------------------------------
# ✅ 合法放置位计算接口
# ---------------------------------------------

@app.route("/api/valid_positions", methods=["POST"])
def valid_positions():
    """
    计算当前摸到的 tile 所有可放置位置（包含 meeple 相关信息）
    """
    tile = board.current_tile
    print(f"📨 当前 tile: {tile.id if tile else 'None'}")

    if tile is None:
        print("⚠️ 当前没有抽到 tile，返回空列表")
        return jsonify([])

    results = board.get_all_suitable_positions(tile)
    print(f"✅ 返回合法放置点共 {len(results)} 项")
    return jsonify(results)


@app.route("/api/valid_positions_without_meeples", methods=["POST"])
def valid_positions_without_meeples():
    """
    只返回 tile 放置合法位，不计算 meeple 放置
    """
    tile = board.current_tile
    print(f"📨 当前 tile: {tile.id if tile else 'None'}")

    if tile is None:
        print("⚠️ 当前没有抽到 tile，返回空列表")
        return jsonify({
            "status": "no_tile",
            "message": "No tile drawn."
        })

    results = board.get_all_suitable_positions(tile, is_add_meeple=False)

    if len(results) == 0:
        print("⚠️ 当前 tile 无法放置，通知前端进行自动重抽")
        return jsonify({
            "status": "need_redraw",
            "message": "The current tile cannot be placed, please redraw."
        })

    print(f"✅ 返回合法放置点共 {len(results)} 项")
    return jsonify({
        "status": "ok",
        "positions": results
    })


# ---------------------------------------------
# ✅ 放置 tile 逻辑
# ---------------------------------------------
import logging

# 配置日志（可选，推荐替换 print）
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@app.route("/api/score", methods=["POST"])
def score():
    try:
        # 获取 JSON 数据
        data = request.get_json()
        if not data:
            logger.debug("❌ 接收到空 JSON 数据")
            return jsonify({"status": "error", "message": "No JSON data provided"}), 400

        # 验证 x, y
        if "x" not in data or "y" not in data:
            logger.debug("❌ JSON 数据缺少 x 或 y 坐标: %s", data)
            return jsonify({"status": "error", "message": "Missing x or y coordinate"}), 400

        x = int(data["x"])
        y = int(data["y"])
        coord = (x, y)
        logger.debug("📍 接收到坐标: %s", coord)

        # 调用 scoring
        logger.debug("🔍 调用 board.scoring(%s)", coord)
        result = board.scoring(coord)
        logger.debug("✅ scoring 返回结果: %s", result)

        if result == ["no tile found"]:
            logger.debug("⚠️ 无板块在坐标 %s", coord)
            return jsonify({"status": "error", "message": "No tile found at coordinate"}), 404

        # 返回结果
        logger.debug("🎉 成功计分，当前玩家: %s", board.round_manager.get_current_player().player_id)
        return jsonify({
            "status": "ok",
            "current_player": board.round_manager.get_current_player().player_id
        }), 200

    except ValueError as e:
        logger.error("❌ 坐标转换错误: %s", str(e))
        return jsonify({"status": "error", "message": f"Invalid coordinate: {str(e)}"}), 400
    except KeyError as e:
        logger.error("❌ JSON 缺少键: %s", str(e))
        return jsonify({"status": "error", "message": f"Missing key: {str(e)}"}), 400
    except Exception as e:
        logger.error("❌ 意外错误: %s", str(e), exc_info=True)  # exc_info=True 包含堆栈跟踪
        return jsonify({"status": "error", "message": f"Unexpected error: {str(e)}"}), 500
@app.route("/api/get_update", methods=["POST"])
def get_update():
    board.round_manager.next_player()

    try:
        # 直接序列化当前回合的增量事件
        report_data = board.round_manager.round_report.serialize()

        return jsonify({
            "status": "ok",
            "data": report_data
        })

    except Exception as e:
        print("❌ 出现错误:", e)
        return jsonify({"status": "error", "message": str(e)}), 500



@app.route("/api/place_tile", methods=["POST"])
def place_tile():
    """
    负责放置 tile 逻辑，同时计算 meeple 放置选项
    """
    try:
        data = request.get_json()
        pos = data["pos"]
        x = pos.get("x")
        y = pos.get("y")
        rotation = pos.get("rotation", 0)

        tile = board.current_tile
        if tile is None:
            return jsonify({"error": "当前没有可用的 tile"}), 400

        board.place_tile(x, y, rotation, tile, None, None, None)

        meeple_placement = board.get_meeple_options_for_position(
            tile, (x, y), rotation, board.round_manager.get_current_player()
        )

        return jsonify({
            "message": "放置tile成功，请放置 meeple",
            "meepleOptions": meeple_placement,
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------
# ✅ 放置 meeple 逻辑
# ---------------------------------------------
@app.route("/api/place_meeple", methods=["POST"])
def place_meeple():
    print("🔥🔥🔥 board.py 里的 place_meeple 函数真正被调用了！")

    try:
        data = request.get_json()
        print("📨 收到前端传入 meeple 放置请求数据：", data)


        coord = tuple(data['coord'])
        feature_id = data['featureId']
        meeple_type = data['meepleType']
        frontend_coord = tuple(data['frontendCoord'])

        print(f"🔍 准备获取玩家 {board.round_manager.get_current_player().name} 的 {meeple_type} meeple")
        player = board.round_manager.get_current_player()
        meeple = player.get_available_meeple_by_type(meeple_type)

        if not meeple:
            print("❌ 当前没有可用 meeple，放置失败")
            return jsonify({"status": "fail", "message": "No available meeple."}), 400

        print(f"🚀 即将执行 board.place_meeple(coord={coord}, feature_id={feature_id}, meeple={meeple}, frontend_coord={frontend_coord})")
        board.place_meeple(coord, feature_id, meeple, frontend_coord)
        print(f"✅ 成功在 {coord} 上放置 meeple (feature {feature_id})")

        return jsonify({"status": "ok"})

    except Exception as e:
        print("🔥🔥🔥 发生异常：", e)
        return jsonify({"status": "fail", "message": str(e)}), 500

# ---------------------------------------------
# ✅ 返回 features 信息
# ---------------------------------------------

@app.route('/api/features', methods=['GET'])
def get_features():
    """
    获取当前所有 feature 状态，供前端渲染
    """
    return jsonify({
        feature_type: [
            {
                "id": feature_id,
                "members": [
                    [list(coord), edge]
                    for coord, edges in fg.tiles.items()
                    for edge in edges
                ]
            }
            for feature_id, fg in board.meta_features[feature_type].items()
        ]
        for feature_type in board.meta_features
    })


# ---------------------------------------------
# ✅ 重启游戏逻辑
# ---------------------------------------------

@app.route("/api/restart", methods=["POST"])
def restart_game():
    """
    完全重置整个游戏局面
    """
    try:
        data = request.get_json() or {}
        player_num = data.get("player_num", 5)
        print("📥 收到重启请求，玩家数 =", player_num)

        board.restart(player_num=player_num)
        print("✅ board.restart 执行完成")

        players_data = [
            {
                "name": player.name,
                "color": player.color,
                "score": player.score,
                "meeples": [
                    {"type": m.type, "id": m.id} for m in player.meeples
                ]
            }
            for player in board.players
        ]

        return jsonify({
            "message": f"新对局已开始，玩家数 = {player_num}",
            "players": players_data
        }), 200

    except Exception as e:
        print("❌ /api/restart 报错：", str(e))
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------
# ✅ 查询当前玩家列表
# ---------------------------------------------

@app.route("/api/players", methods=["GET"])
def get_players():
    """
    获取当前所有玩家状态
    """
    try:
        result = []
        for player in board.round_manager.players:
            active_meeples = [
                {"type": m.type, "id": m.id}
                for m in player.meeples
                if not m.active
            ]
            result.append({
                "name": player.name,
                "color": player.color,
                "score": player.score,
                "meeples": active_meeples
            })
        print(result)
        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------
# ✅ 启动 Flask 服务
# ---------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)
