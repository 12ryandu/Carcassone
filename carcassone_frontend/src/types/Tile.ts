// 前端编辑用
export interface FeatureEditor {
    id: number;
    type: '草坪' | '城' | '路' | '修道院';
    connectedEdges: number[];
    hasShield?: boolean;
    hasDouble?: boolean;
    hasInn?: boolean;
}

export interface TileEditor {
    id: number;
    features: FeatureEditor[];
    image?: string;
}

// 提交给后端的格式
export interface FeaturePayload {
    id: string;
    name: string;
    description: string;
}

export interface TilePayload {
    id: number;
    image: string;
    features: FeaturePayload[];
}
