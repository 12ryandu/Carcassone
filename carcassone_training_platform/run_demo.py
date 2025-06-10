from env.board import GameBoard

board = GameBoard()
board.load_stack_from_file("tile_store/tiles.json")
board.shuffle_stack()

print(f"✅ 共载入 {len(board.stack)} 张 tile，开始抽一张：")
tile = board.draw_tile()
print("🧩 抽到 tile:", tile.features)

board.get_init_tile_and_place_by_id(1747541545336)

while board.stack:
    tile = board.draw_tile()
    board.get_all_suitable_positions(tile)
