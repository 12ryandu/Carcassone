import React, { useEffect, useState } from 'react';
import './TileMap.css';


interface MeepleInfo {
    coord: [number, number];
    featureType: string;
    featureId: number;
    frontendCoord: [number, number];
    meepleType: string;
}

interface Tile {
    x: number;
    y: number;
    id: number;
    rotation: number;
    meeples?: MeepleInfo[]; // 👈 新增
}

interface Position {
    is_put:boolean;
    coord: [number, number];
    rotation: number;
    featureType: string;
    featureId: number;
    frontend_coord: [number, number];
    meepleType: string;
}

interface SimplePosition {
    coord: [number, number];
    rotation: number;
}

interface Feature {
    id: number;
    members: [number[], number][];
}

interface FeatureMap {
    [key: string]: Feature[];
}

interface Player {
    name: string;
    color: string;
    score: number;
    meeples: { type: string; id: number }[];
}

const TileMap: React.FC = () => {
    const tileSize = 100;
    const [currentPlayerIndex, setCurrentPlayerIndex] = useState<number | null>(null);
    const [tiles, setTiles] = useState<Tile[]>([]);
    const [drawnTile, setDrawnTile] = useState<{ id: number; rotation: number } | null>(null);
    const [validPositions, setValidPositions] = useState<SimplePosition[]>([]);
    const [features, setFeatures] = useState<FeatureMap>({});

    const [players, setPlayers] = useState<Player[]>([]);
    const [showHints, setShowHints] = useState(true);
    const [placementPhase, setPlacementPhase] = useState<"idle"| "draw" | "tile" | "meeple" | "score" | "event" >( "idle" );
    const [meepleOptions, setMeepleOptions] = useState<MeepleInfo[]>([]);
    const [activeHintKey, setActiveHintKey] = useState<string | null>(null);
    const [lastPlacedCoord, setLastPlacedCoord] = useState<{x: number, y: number} | null>(null);


    interface SelectedPosition {
        coord: [number, number];
        rotation: number;
    }
    const [selectedPosition, setSelectedPosition] = useState<SelectedPosition | null>(null);

    interface RotationMap {
        [coordKey: string]: number[]; // key是coord字符串，value是合法rotations
    }
    const [rotationMap, setRotationMap] = useState<RotationMap>({});


    const [minX, setMinX] = useState(0);
    const [maxX, setMaxX] = useState(0);
    const [minY, setMinY] = useState(0);
    const [maxY, setMaxY] = useState(0);



    const fetchMap = async () => {
        const res = await fetch('http://localhost:5000/api/map');
        const data = await res.json();
        setTiles(data);
        const xs = data.map((tile: Tile) => tile.x);
        const ys = data.map((tile: Tile) => tile.y);
        setMinX(Math.min(...xs) - 1);
        setMaxX(Math.max(...xs) + 1);
        setMinY(Math.min(...ys) - 1);
        setMaxY(Math.max(...ys) + 1);
    };

    const fetchFeatures = async () => {
        const res = await fetch('http://localhost:5000/api/features');
        const data = await res.json();
        setFeatures(data);
    };

    const fetchPlayers = async () => {
        const res = await fetch('http://localhost:5000/api/players');
        const data = await res.json();
        setPlayers(data);
        return data;
    };

    const nextPhase = () => {
        switch (placementPhase) {
            case "draw":
                setPlacementPhase("tile");
                break;
            case "tile":
                setPlacementPhase("meeple");
                break;
            case "meeple":
                setPlacementPhase("score");
                break;
            case "score":
                setPlacementPhase("event");
                break;
            case "event":
                setPlacementPhase("idle");
                break;
        }
    };


    const fetchDrawTile = async (): Promise<{ id: number, rotation: number } | null> => {
        try {
            const res = await fetch('http://localhost:5000/api/draw_tile', { method: 'POST' });
            const data = await res.json();

            if (data.error) {
                alert(`❌ 无法抽牌: ${data.error}`);
                return null;
            }

            setDrawnTile({ id: data.id, rotation: data.rotation });
            setValidPositions([]);
            await fetchValidPositions();
            setPlacementPhase("tile");

            return { id: data.id, rotation: data.rotation };
        } catch (error) {
            console.error("❌ 抽牌失败:", error);
            alert("❌ 网络请求失败");
            return null;
        }
    };

    const fetchValidPositions = async () => {
        const res = await fetch('http://localhost:5000/api/valid_positions_without_meeples', {
            method: 'POST'
        });
        const data = await res.json();

        if (data.status === 'ok') {
            const positions = data.positions;  // ✅ 核心区别在这里

            setValidPositions(positions);

            // 你原来的 rotationMap 逻辑完全照抄
            const tempMap: RotationMap = {};
            positions.forEach((pos: Position) => {
                const key = `${pos.coord[0]},${pos.coord[1]}`;
                if (!(key in tempMap)) {
                    tempMap[key] = [];
                }
                tempMap[key].push(pos.rotation);
            });
            setRotationMap(tempMap);
        }
        else if (data.status === 'need_redraw') {
            console.log("⚠️ 服务器提示需要重抽牌");
            alert("当前 tile 无法放置，已自动重抽一张牌！");
            await fetchDrawTile();
            await fetchValidPositions();
        }
        else if (data.status === 'no_tile') {
            console.log("⚠️ 服务器提示牌堆已耗尽");
            alert("所有牌已放置完毕，游戏结束！");
        }
    };


    const rotateCurrent = () => {
        if (!selectedPosition) return;

        const key = `${selectedPosition.coord[0]},${selectedPosition.coord[1]}`;
        const validRotations = rotationMap[key]?.sort() ?? [];

        if (validRotations.length === 0) return;

        const currentIndex = validRotations.indexOf(selectedPosition.rotation);
        const nextRotation = validRotations[(currentIndex + 1) % validRotations.length];

        setSelectedPosition({
            coord: selectedPosition.coord,
            rotation: nextRotation
        });
    };
    const canRotate = () => {
        if (!selectedPosition) return false;

        const key = `${selectedPosition.coord[0]},${selectedPosition.coord[1]}`;
        const validRotations = rotationMap[key] ?? [];

        return validRotations.length > 1;
    };
    useEffect(() => {
        if (selectedPosition) {
            console.log("🌀 当前选中：", selectedPosition.coord, "rotation:", selectedPosition.rotation);
        } else {
            console.log("🌀 当前未选中任何位置");
        }
    }, [selectedPosition]);

    const handleConfirmPlacementNew = async () => {
        if (!selectedPosition || !drawnTile) {
            console.log("❌ 没有选中合法位或还未抽牌");
            return;
        }

        const requestBody = {
            id: drawnTile.id,
            pos: {
                x: selectedPosition.coord[0],
                y: selectedPosition.coord[1],
                rotation: selectedPosition.rotation
            }
        };

        console.log("📤 正在发送纯放置请求: ", requestBody);

        try {
            const res = await fetch('http://localhost:5000/api/place_tile', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody)
            });

            const rawData = await res.json();

            if (rawData.error) {
                console.error("❌ 服务器返回错误:", rawData.error);
                alert(`❌ 错误: ${rawData.error}`);
                return;
            }

            console.log("✅ 后端返回合法 meeple 放置: ", rawData);

            // ✅ ✅ ✅ 直接更新 tiles 列表 (本地追加)
            setTiles(prevTiles => [
                ...prevTiles,
                {
                    x: selectedPosition.coord[0],
                    y: selectedPosition.coord[1],
                    id: drawnTile.id,
                    rotation: -1*selectedPosition.rotation,
                    meeples: []
                }
            ]);
            setLastPlacedCoord({
                x: selectedPosition.coord[0],
                y: selectedPosition.coord[1]
            });
            console.log(`📍 更新最新放置坐标：(${selectedPosition.coord[0]}, ${selectedPosition.coord[1]})`);

            // ✅ 重新计算地图范围
            setMinX(prev => Math.min(prev, selectedPosition.coord[0] - 1));
            setMaxX(prev => Math.max(prev, selectedPosition.coord[0] + 1));
            setMinY(prev => Math.min(prev, selectedPosition.coord[1] - 1));
            setMaxY(prev => Math.max(prev, selectedPosition.coord[1] + 1));

            // 🟢 判断是否有 meepleOptions
            if (rawData.meepleOptions && rawData.meepleOptions.length > 0) {
                const data = rawData.meepleOptions.map((item: any, idx: number) => {
                    console.log(`🧍 Meeple 放置点 #${idx + 1}`);
                    console.log(`  ➤ 坐标: (${item.coord[0]}, ${item.coord[1]})`);
                    console.log(`  ➤ 特征类型: ${item.featureType}`);
                    console.log(`  ➤ 特征ID: ${item.featureId}`);
                    console.log(`  ➤ Meeple类型: ${item.meepleType}`);
                    console.log(`  ➤ frontend位置: (${item.frontend_coord[0]}%, ${item.frontend_coord[1]}%)`);
                    return {
                        coord: item.coord,
                        featureType: item.featureType,
                        featureId: item.featureId,
                        frontendCoord: item.frontend_coord,
                        meepleType: item.meepleType,
                        rotation: item.rotation
                    };
                });
                setSelectedPosition(null);  // ✅ 清除选中位置
                setMeepleOptions(data);
                console.log("🧩 进入 Meeple 放置阶段，共", data.length, "个可放置点");
                setPlacementPhase("meeple");
            } else {
                console.log("🧩 无需放置 Meeple，直接进入下一回合");
                setPlacementPhase("score");
                handleScore()
            }
        } catch (error) {
            console.error("❌ 网络请求失败:", error);
            alert("❌ 网络请求失败");
        }
    };


    const handleRestartGame = async () => {
        const res = await fetch('http://localhost:5000/api/restart', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ player_num: 5 })
        });
        const data = await res.json();

        await fetchMap();
        await fetchFeatures();
        await fetchPlayers();

        setValidPositions([]);
        setDrawnTile(null);
        setSelectedPosition(null);
        setMeepleOptions([]);

        // ✅ 立刻进入抽牌逻辑
        const drawnTile = await fetchDrawTile();

        if (!drawnTile) {
            console.error("❌ 重启时抽牌失败");
            return;
        }

        console.log("✅ 已抽取第一张牌:", drawnTile);
    };



    const handlePresetMap = async () => {
        await fetch('http://localhost:5000/api/preset_map', {
            method: 'POST'
        });
        await fetchMap();
        await fetchFeatures();
        await fetchPlayers();
    };

    useEffect(() => {
        fetchMap();
        fetchFeatures();
        fetchPlayers().then(() => setCurrentPlayerIndex(0));

    }, []);

    const getTileStyle = (tile: Tile): React.CSSProperties => ({
        position: 'absolute',
        top: `${(tile.y - minY) * tileSize}px`,
        left: `${(tile.x - minX) * tileSize}px`,
        width: `${tileSize}px`,
        height: `${tileSize}px`,
        transform: `rotate(${tile.rotation * 90}deg)`,
        transformOrigin: 'center',
        border: '1px solid #ccc'
    });
    const skipMeeplePlacement = () => {
        console.log("❌ 点击红叉，跳过 Meeple 放置");
        setPlacementPhase("score");
        handleScore();
    };

    const handleScore = async () => {
        try {
            // 验证 lastPlacedCoord
            if (!lastPlacedCoord) {
                console.log("❌ 无最新放置坐标");
                alert("无法计分：未找到最新放置的板块");
                return;
            }

            console.log(`📊 发送计分请求，坐标：(${lastPlacedCoord.x}, ${lastPlacedCoord.y})`);

            // 发送 POST 请求到 /api/score
            const response = await fetch('http://localhost:5000/api/score', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    x: lastPlacedCoord.x,
                    y: lastPlacedCoord.y,
                }),
            });

            // 检查 HTTP 状态
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.message || `HTTP error: ${response.status}`);
            }

            const data = await response.json();

            // 记录响应
            console.log("✅ 计分响应：", data);

            // 处理响应
            if (data.status !== 'ok') {
                console.error(`❌ 计分失败：${data.message}`);
                alert(`计分失败：${data.message}`);
                return;
            }

            // 更新当前玩家（如果需要）
            if (data.current_player) {
                console.log(`🎮 当前玩家：${data.current_player}`);
                setCurrentPlayerIndex(data.current_player); // 假设有此状态
            }

            // 切换阶段并触发事件
            setPlacementPhase('event');
            await handleEvent(); // 确保 await，因为 handleEvent 是 async

        } catch (error) {
            // 安全处理错误（修复 TS18046）
            const errorMessage = error instanceof Error ? error.message : String(error);
            console.error("❌ 计分失败:", errorMessage);
            alert(`计分失败：${errorMessage}`);
        }
    };

    const handleEvent = async () => {
        try {
            console.log("📡 正在获取本回合事件流...");

            const res = await fetch('http://localhost:5000/api/get_update', { method: 'POST' });
            const data = await res.json();

            if (data.status === "ok") {
                console.log("✅ 获取到回合更新:", data);
                console.log("🧩 事件流：", data.report);
                console.log("🗺 全局 features：", data.features);

                // ✅ 这里暂时不做 patch，仅打印调试
            } else {
                console.warn("⚠️ 未收到正常更新：", data);
            }

            // 🔄 正常进入下一阶段（抽新牌）
            setPlacementPhase("draw");
            fetchDrawTile();

        } catch (error) {
            console.error("❌ 获取更新失败:", error);
            alert("❌ 获取更新失败");
        }
    }





    const handleMeeplePlacement = async (option:MeepleInfo | null) => {
        if (option === null) {
            // ✅ 直接跳过，进入下一阶段，无需发请求
            setPlacementPhase("score");
            handleScore();
            return;
        }

        try {
            const res = await fetch('http://localhost:5000/api/place_meeple', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(option)
            });

            const data = await res.json();

            if (data.error) {
                console.error("❌ Meeple放置失败:", data.error);
                alert(`❌ 错误: ${data.error}`);
                return;
            }

            console.log("✅ Meeple放置成功:", data);
            setPlacementPhase("score")
            handleScore()
        } catch (error) {
            console.error("❌ 网络请求失败:", error);
            alert("❌ 网络请求失败");
        }
    };

    const mapWidth = (maxX - minX + 1) * tileSize;
    const mapHeight = (maxY - minY + 1) * tileSize;

    const fetchUpdate = async () => {
        try {
            const res = await fetch('http://localhost:5000/api/get_update', { method: 'POST' });
            const data = await res.json();

            console.log("✅ 获取到回合更新:", data);

            // 👉 先只打印，不做应用
            if (data.status === "ok") {
                console.log("事件流：", data.report);
                console.log("全局 features：", data.features);
            } else {
                console.warn("⚠️ 未收到正常更新：", data);
            }
        } catch (error) {
            console.error("❌ 获取更新失败:", error);
            alert("❌ 获取更新失败");
        }
    };
    // 👉 按 [x,y,frontendX,frontendY] 分组
    const groupedMeepleOptions: {
        key: string;
        coord: [number, number];
        frontendCoord: [number, number];
        options: MeepleInfo[];
    }[] = [];

    const seen = new Map<string, MeepleInfo[]>();

    meepleOptions.forEach((item) => {
        const key = `${item.coord[0]},${item.coord[1]}-${item.frontendCoord[0]},${item.frontendCoord[1]}`;
        if (!seen.has(key)) seen.set(key, []);
        seen.get(key)!.push(item);
    });

    for (const [key, options] of seen.entries()) {
        groupedMeepleOptions.push({
            key,
            coord: options[0].coord,
            frontendCoord: options[0].frontendCoord,
            options
        });
    }




    return (

        <div style={{ display: 'flex' }}>
             {/* 🎯 当前玩家浮窗显示 */}
            {/* 🧮 常驻玩家信息栏 */}
            <div style={{
                position: 'fixed',
                top: 10,
                left: '50%',
                transform: 'translateX(-50%)',
                backgroundColor: '#fffde7',
                border: '1px solid #fbc02d',
                borderRadius: '10px',
                padding: '10px 20px',
                boxShadow: '0 2px 6px rgba(0,0,0,0.15)',
                zIndex: 1000
            }}>
                {currentPlayerIndex !== null && (
                    <>
                        🎯 当前玩家: {players[currentPlayerIndex]?.name} &nbsp;|&nbsp;
                        🧍‍♂️ Meeple剩余: {players[currentPlayerIndex]?.meeples.length} &nbsp;|&nbsp;
                        🏆 分数: {players[currentPlayerIndex]?.score}
                    </>
                )}
            </div>

            {/* 🧩 左侧 Feature 列表 */}
            <div style={{ width: '260px', padding: '20px', backgroundColor: '#f4f4f4', borderRight: '1px solid #ccc', overflowY: 'auto' }}>
                <h3>📋 当前 Feature</h3>
                {Object.keys(features).map(type => (
                    <div key={type}>
                        <h4>{type}</h4>
                        <ul style={{ paddingLeft: '16px' }}>
                            {features[type].map((f, idx) => (
                                <li key={idx}>
                                    ID: {f.id}, Members: {f.members.map(([coord, edge]) => `(${coord[0]}, ${coord[1]} @ ${edge})`).join(', ')}
                                </li>
                            ))}
                        </ul>
                    </div>
                ))}
            </div>

            {/* 🎯 主内容区域 */}
            <div style={{ padding: '30px', flex: 1 }}>
                {/* 🎮 固定玩家栏 */}
                <div className="fixed-player-panel">
                    <h3 style={{ textAlign: 'center' }}>🎮 玩家</h3>
                    {players.map((player, idx) => (
                        <div
                            key={idx}
                            className={`player-entry ${idx === currentPlayerIndex ? 'highlight-current' : ''}`}
                        >
                            <span className="player-score">🏆 {player.score}</span>
                            <span className="player-name">{player.name}</span>
                            <div className="player-meeples">
                                {player.meeples.map((meeple, mIdx) => (
                                    <img
                                        key={mIdx}
                                        src="/meeple_normal_scaled.svg"
                                        alt="meeple"
                                        className="meeple-3d"
                                        style={{ color: player.color }}
                                    />
                                ))}
                            </div>
                        </div>
                    ))}
                </div>

                {/* 🧩 控制按钮区域 */}
                <h2 className="tile-map-title">🧩 Tile 地图可视化</h2>
                <div className="tile-map-controls">
                    <button onClick={fetchMap}>🔁 查看地图</button>
                    <button onClick={handlePresetMap}>📌 添加固定地图</button>
                    <button onClick={handleRestartGame}>🔄 重新开始</button>
                    <button onClick={() => setShowHints(prev => !prev)}>
                        {showHints ? '🙈 隐藏提示区域' : '🎯 显示提示区域'}
                    </button>
                </div>

                {/* 🎴 当前摸到的牌预览 */}
                {placementPhase === "tile" && drawnTile && (
                    <div className="drawn-tile-wrapper">
                        <div className="drawn-tile-box">
                            <h4>🎴 当前摸到的牌</h4>
                            <img
                                src={`${process.env.REACT_APP_R2_PUBLIC_BASE_URL}/tile-${drawnTile.id}.png`}
                                alt={`drawn-tile-${drawnTile.id}`}
                                style={{
                                    width: `${tileSize}px`,
                                    height: `${tileSize}px`,
                                    transform: `rotate(${drawnTile.rotation * 90}deg)`,
                                    transformOrigin: 'center'
                                }}
                            />
                            <div>Tile ID: {drawnTile.id}</div>
                        </div>
                    </div>
                )}

                {/* 地图主视图 */}
                <div style={{ position: 'relative', width: `${mapWidth}px`, height: `${mapHeight}px`, margin: '0 auto', backgroundColor: '#f9f9f9', border: '2px solid #ddd' }}>
                    {tiles.map(tile => {
                        return (
                            <React.Fragment key={`tile-${tile.x}-${tile.y}`}>
                                <img
                                    src={`${process.env.REACT_APP_R2_PUBLIC_BASE_URL}/tile-${tile.id}.png`}
                                    alt={`tile-${tile.id}`}
                                    style={getTileStyle(tile)}
                                />

                                {/* 渲染已放置的 meeple */}
                                {tile.meeples && tile.meeples.map((meeple, idx) => (
                                    <div
                                        key={`meeple-${idx}`}
                                        style={{
                                            position: 'absolute',
                                            top: `${(tile.y - minY) * tileSize + (meeple.frontendCoord[1] / 100) * tileSize - 20}px`,
                                            left: `${(tile.x - minX) * tileSize + (meeple.frontendCoord[0] / 100) * tileSize - 10}px`,
                                            fontSize: '24px',
                                            zIndex: 30
                                        }}
                                    >
                                        👤 {/* 你也可以把这里的图标换成真正的 meeple SVG */}
                                    </div>
                                ))}
                            </React.Fragment>
                        );
                    })}

                    { placementPhase === "tile" && validPositions.map((pos, idx) => {
                        if (currentPlayerIndex === null) return null;

                        const isSelected = selectedPosition?.coord[0] === pos.coord[0] && selectedPosition?.coord[1] === pos.coord[1];

                        return (
                            <div
                                key={`valid-${idx}`}
                                style={{
                                    position: 'absolute',
                                    left: `${(pos.coord[0] - minX) * tileSize}px`,
                                    top: `${(pos.coord[1] - minY) * tileSize}px`,
                                    width: `${tileSize}px`,
                                    height: `${tileSize}px`,
                                    backgroundColor: isSelected
                                        ? `rgba(100, 150, 255, 0.3)`
                                        : `rgba(100, 150, 255, 0.05)`,
                                    borderRadius: '8px',
                                    boxShadow: isSelected
                                        ? `0 0 12px rgba(100, 150, 255, 0.6)`
                                        : `0 0 4px rgba(100, 150, 255, 0.3)`,
                                    transition: 'transform 0.3s, box-shadow 0.3s',
                                    animation: 'floating 2s infinite ease-in-out',
                                    zIndex: 10,
                                    cursor: 'pointer',
                                }}
                                onClick={() => setSelectedPosition(pos)}
                            >
                                {isSelected && drawnTile && (
                                    <img
                                        src={`${process.env.REACT_APP_R2_PUBLIC_BASE_URL}/tile-${drawnTile.id}.png`}
                                        alt={`preview-tile-${drawnTile.id}`}
                                        style={{
                                            width: '100%',
                                            height: '100%',
                                            transform: `rotate(${(selectedPosition?.rotation ?? 0) * -90}deg)`,
                                            transformOrigin: 'center',
                                            pointerEvents: 'none'
                                        }}
                                    />
                                )}

                            </div>
                        );
                    })}
                    {selectedPosition && (
                        <>
                            {/* 旋转按钮 */}
                            {canRotate() && (
                                <div
                                    style={{
                                        position: 'absolute',
                                        left: `${(selectedPosition.coord[0] - minX) * tileSize + tileSize - 20}px`,
                                        top: `${(selectedPosition.coord[1] - minY) * tileSize - 10}px`,
                                        cursor: 'pointer',
                                        zIndex: 100,
                                        animation: 'floatingSmall 2s infinite ease-in-out',
                                    }}
                                    onClick={rotateCurrent}
                                >
                                    <img
                                        src="/rotate.png"
                                        alt="rotate"
                                        style={{ width: '28px', height: '28px', userSelect: 'none', pointerEvents: 'none' }}
                                    />
                                </div>
                            )}

                            {/* ✅ 确认对勾按钮 */}
                            <div
                                style={{
                                    position: 'absolute',
                                    left: `${(selectedPosition.coord[0] - minX) * tileSize + tileSize - 20}px`,
                                    top: `${(selectedPosition.coord[1] - minY) * tileSize + 30}px`,  // 比旋转按钮稍微下移一点
                                    cursor: 'pointer',
                                    zIndex: 100,
                                    animation: 'floatingSmall 2s infinite ease-in-out',
                                }}
                                onClick={handleConfirmPlacementNew}

                            >
                                <img
                                    src="/confirm.png"
                                    alt="confirm"
                                    style={{ width: '28px', height: '28px', userSelect: 'none', pointerEvents: 'none' }}
                                />
                            </div>
                        </>
                    )}
                    {/* 🧍‍♂️ Meeple 可放置点浮动箭头 */}
                    {placementPhase === "meeple" && groupedMeepleOptions.map((group, idx) => {
                        const { coord, frontendCoord, key } = group;
                        const isActive = activeHintKey === key;

                        return (
                            <React.Fragment key={`meeple-group-${key}`}>
                                {/* ➤箭头提示 */}
                                <div
                                    style={{
                                        position: 'absolute',
                                        top: `${(coord[1] - minY) * tileSize + (frontendCoord[1] / 100) * tileSize - 18}px`,
                                        left: `${(coord[0] - minX) * tileSize + (frontendCoord[0] / 100) * tileSize - 8}px`,
                                        fontSize: '20px',
                                        zIndex: 50,
                                        transform: 'rotate(90deg)',
                                        cursor: 'pointer',
                                        userSelect: 'none'
                                    }}
                                    onClick={() => setActiveHintKey(isActive ? null : key)}
                                >
                                    ➤
                                </div>

                                {/* ⬆️ 弹出面板 */}
                                {isActive && (
                                    <div
                                        style={{
                                            position: 'absolute',
                                            top: `${(coord[1] - minY) * tileSize + (frontendCoord[1] / 100) * tileSize - 60}px`,
                                            left: `${(coord[0] - minX) * tileSize + (frontendCoord[0] / 100) * tileSize - 40}px`,
                                            backgroundColor: '#fff8e1',
                                            border: '1px solid #fbc02d',
                                            borderRadius: '6px',
                                            padding: '8px 12px',
                                            zIndex: 60,
                                            boxShadow: '0 2px 8px rgba(0,0,0,0.15)'
                                        }}
                                    >
                                        {group.options.map((option, i) => (
                                            <button
                                                key={i}
                                                style={{
                                                    margin: '4px',
                                                    padding: '6px 10px',
                                                    borderRadius: '4px',
                                                    backgroundColor: '#aed581',
                                                    border: '1px solid #689f38',
                                                    cursor: 'pointer',
                                                    fontSize: '12px'
                                                }}
                                                onClick={() => handleMeeplePlacement(option)}
                                            >
                                                {option.meepleType} 放置
                                            </button>
                                        ))}
                                    </div>
                                )}
                                {/* 红叉按钮在 Tile 外侧左上角 */}
                                <div
                                    style={{
                                        position: 'absolute',
                                        top: `${(coord[1] - minY) * tileSize - 20 }px`, // 外侧左上角，向上偏移 10px
                                        left: `${(coord[0] - minX) * tileSize - 30 }px`, // 外侧左上角，向左偏移 10px
                                        zIndex: 20, // 低于米宝箭头 (zIndex: 50)，避免遮挡
                                    }}
                                >
                                    <span
                                        onClick={skipMeeplePlacement}
                                        style={{
                                            margin: '4px',
                                            padding: '6px 10px', // 保留内边距以确保点击区域
                                            fontSize: '16px', // 调整字体大小，使 ❌ 更突出
                                            color: '#f44336', // 红色文字，替代背景
                                            cursor: 'pointer',
                                            userSelect: 'none',
                                            backgroundColor: 'transparent', // 透明背景
                                            border: 'none', // 移除边框
                                        }}
                                    >
                                        ❌
                                    </span>
                                </div>
                            </React.Fragment>
                        );
                    })}
                </div>
            </div>
        </div>
    );
};

export default TileMap;
