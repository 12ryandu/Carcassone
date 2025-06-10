import React, { useState } from 'react';
import uploadImageToR2, { deleteImageFromR2 } from './utils/uploadImageToR2';
import './App.css';
import {useNavigate} from "react-router-dom";

type TileFeatureType = '草坪' | '城' | '路' | '修道院' | '小花园';

interface BaseFeature {
    id: number;
    type: TileFeatureType;
    connectedEdges: number[];
}

interface CityFeature extends BaseFeature {
    hasShield: boolean;
    hasDouble: boolean;
}

interface RoadFeature extends BaseFeature {
    hasInn: boolean;
}

type Feature = BaseFeature | CityFeature | RoadFeature;

interface TileCard {
    id: number;
    features: Feature[];
}

const App: React.FC = () => {
    const [tiles, setTiles] = useState<TileCard[]>([]);
    const [imageVersions, setImageVersions] = useState<Record<number, number>>({});
    const [successVisible, setSuccessVisible] = useState(false);
    const [uploadSuccessVisible, setUploadSuccessVisible] = useState(false);

    const handleNewTile = () => {
        const newTile: TileCard = {
            id: Date.now(),
            features: [],
        };
        setTiles([...tiles, newTile]);
    };

    const handleAddFeature = (tileId: number) => {
        setTiles(tiles.map(tile =>
            tile.id === tileId
                ? {
                    ...tile,
                    features: [...tile.features, {
                        id: Date.now() + Math.random(),
                        type: '草坪',
                        connectedEdges: [],
                    }],
                }
                : tile
        ));
    };

    const handleFeatureTypeChange = (tileId: number, featureId: number, newType: TileFeatureType) => {
        setTiles(tiles.map(tile =>
            tile.id === tileId
                ? {
                    ...tile,
                    features: tile.features.map(f =>
                        f.id === featureId
                            ? {
                                ...f,
                                type: newType,
                                connectedEdges: [],
                                ...(newType === '城' ? { hasShield: false, hasDouble: false } : {}),
                                ...(newType === '路' ? { hasInn: false } : {}),
                            }
                            : f
                    ),
                }
                : tile
        ));
    };

    const handleFeatureEdgeChange = (tileId: number, featureId: number, raw: string) => {
        const digits = Array.from(raw).filter(c => /[0-7]/.test(c)).map(c => parseInt(c));
        setTiles(tiles.map(tile =>
            tile.id === tileId
                ? {
                    ...tile,
                    features: tile.features.map(f =>
                        f.id === featureId
                            ? { ...f, connectedEdges: digits }
                            : f
                    ),
                }
                : tile
        ));
    };

    const handleCheckboxChange = (tileId: number, featureId: number, field: string, checked: boolean) => {
        setTiles(tiles.map(tile =>
            tile.id === tileId
                ? {
                    ...tile,
                    features: tile.features.map(f =>
                        f.id === featureId ? { ...f, [field]: checked } : f
                    ),
                }
                : tile
        ));
    };

    const handleRemoveFeature = (tileId: number, featureId: number) => {
        setTiles(tiles.map(tile =>
            tile.id === tileId
                ? {
                    ...tile,
                    features: tile.features.filter(f => f.id !== featureId),
                }
                : tile
        ));
    };

    const handleSubmitTile = async (tile: TileCard) => {
        const payload = {
            id: tile.id,
            features: tile.features.map(f => {
                const base = {
                    name:
                        f.type === '草坪' ? 'FieldFeature' :
                            f.type === '城' ? 'CityFeature' :
                                f.type === '路' ? 'RoadFeature' :
                                    f.type === '小花园' ? 'GardenFeature' :
                                        'CloisterFeature',
                };

                if (f.type === '草坪') {
                    return { ...base, connectedEdges: f.connectedEdges };
                }
                if (f.type === '城') {
                    return {
                        ...base,
                        connectedEdges: f.connectedEdges,
                        hasShield: (f as CityFeature).hasShield,
                        hasDouble: (f as CityFeature).hasDouble,
                    };
                }
                if (f.type === '路') {
                    return {
                        ...base,
                        connectedEdges: f.connectedEdges,
                        hasInn: (f as RoadFeature).hasInn,
                    };
                }
                if (f.type === '小花园') {
                    return { ...base, connectedEdges: [] };
                }

                return base;
            })
        };

        try {
            const res = await fetch('http://localhost:5000/add_tile', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            if (res.ok) {
                setSuccessVisible(true);
                setTimeout(() => setSuccessVisible(false), 3000);
            }
        } catch (e) {
            console.error(e);
            alert('Error during upload.');
        }
    };
    const navigate = useNavigate();

    return (
        <div style={{ padding: '100px' }}>
            <div className="fixed-button">
                <h2>🧩 Tile 录入器</h2>
                <button onClick={handleNewTile}>新建 Tile</button>
                <button
                    style={{ marginLeft: '20px', backgroundColor: '#2196F3', color: 'white' }}
                    onClick={() => navigate('/map')}
                >
                    🗺️ 查看地图
                </button>
            </div>

            {tiles.map(tile => (
                <div key={tile.id} style={{ border: '1px solid #ccc', marginTop: '20px', padding: '20px', borderRadius: '8px' }}>
                    <h3>Tile #{tile.id}</h3>

                    <div style={{ marginTop: '10px' }}>
                        <strong>部件：</strong>
                        {tile.features.map(feature => (
                            <div key={feature.id} style={{ marginTop: '10px', borderBottom: '1px solid #ddd', paddingBottom: '10px' }}>
                                类型：
                                <select
                                    value={feature.type}
                                    onChange={e => handleFeatureTypeChange(tile.id, feature.id, e.target.value as TileFeatureType)}
                                >
                                    <option value="草坪">草坪</option>
                                    <option value="城">城</option>
                                    <option value="路">路</option>
                                    <option value="修道院">修道院</option>
                                    <option value="小花园">小花园</option>
                                </select>

                                {feature.type !== '小花园' && (
                                    <div style={{ marginTop: '5px' }}>
                                        connectedEdges:
                                        <input
                                            type="text"
                                            placeholder="只允许输入 0-7"
                                            value={feature.connectedEdges?.join(',') || ''}
                                            onChange={e => handleFeatureEdgeChange(tile.id, feature.id, e.target.value)}
                                        />
                                    </div>
                                )}

                                {feature.type === '城' && (
                                    <>
                                        <label>
                                            <input
                                                type="checkbox"
                                                checked={(feature as CityFeature).hasShield || false}
                                                onChange={e => handleCheckboxChange(tile.id, feature.id, 'hasShield', e.target.checked)}
                                            /> hasShield
                                        </label><br />
                                        <label>
                                            <input
                                                type="checkbox"
                                                checked={(feature as CityFeature).hasDouble || false}
                                                onChange={e => handleCheckboxChange(tile.id, feature.id, 'hasDouble', e.target.checked)}
                                            /> hasDouble
                                        </label>
                                    </>
                                )}

                                {feature.type === '路' && (
                                    <label>
                                        <input
                                            type="checkbox"
                                            checked={(feature as RoadFeature).hasInn || false}
                                            onChange={e => handleCheckboxChange(tile.id, feature.id, 'hasInn', e.target.checked)}
                                        /> hasInn
                                    </label>
                                )}

                                <div>
                                    <button onClick={() => handleRemoveFeature(tile.id, feature.id)} style={{ marginTop: '5px' }}>删除部件</button>
                                </div>
                            </div>
                        ))}
                        <button onClick={() => handleAddFeature(tile.id)} style={{ marginTop: '10px' }}>➕ 添加部件</button>
                    </div>

                    <div style={{ marginTop: '10px' }}>
                        <strong>上传图片：</strong>
                        <input
                            type="file"
                            accept="image/*"
                            onChange={async (e) => {
                                const file = e.target.files?.[0];
                                if (file) {
                                    try {
                                        await uploadImageToR2(file, tile.id);
                                        setImageVersions(prev => ({ ...prev, [tile.id]: Date.now() }));
                                        console.log('图片上传成功！');
                                    } catch (err) {
                                        console.error(err);
                                        console.log('上传失败');
                                    }
                                }
                            }}
                        />

                        {imageVersions[tile.id] && (
                            <>
                                <div style={{ marginTop: '10px' }}>
                                    <img
                                        src={`${process.env.REACT_APP_R2_PUBLIC_BASE_URL}/tile-${tile.id}.png?v=${imageVersions[tile.id]}`}
                                        alt="预览图"
                                        style={{ maxWidth: '100px', marginTop: '5px' }}
                                    />
                                </div>
                                <button
                                    onClick={async () => {
                                        try {
                                            await deleteImageFromR2(tile.id);
                                            setImageVersions(prev => {
                                                const updated = { ...prev };
                                                delete updated[tile.id];
                                                return updated;
                                            });
                                            alert('图片已删除！');
                                        } catch (err) {
                                            console.error(err);
                                            alert('删除失败！');
                                        }
                                    }}
                                    style={{ marginTop: '5px', backgroundColor: '#f44336', color: 'white' }}
                                >
                                    🗑️ 删除图片
                                </button>
                            </>
                        )}
                    </div>

                    <button
                        onClick={() => handleSubmitTile(tile)}
                        style={{ marginTop: '20px', backgroundColor: '#4CAF50', color: 'white', padding: '10px' }}
                    >
                        ⬆️ 提交 Tile
                    </button>
                </div>
            ))}
        </div>
    );
};

export default App;
