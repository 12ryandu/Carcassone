import AWS from 'aws-sdk';

console.log('🔧 ENV CONFIG:', {
    accessKeyId: process.env.REACT_APP_R2_ACCESS_KEY_ID,
    secretAccessKey: process.env.REACT_APP_R2_SECRET_ACCESS_KEY,
    endpoint: process.env.REACT_APP_R2_ENDPOINT,
    bucket: process.env.REACT_APP_R2_BUCKET,
});

const accessKeyId = process.env.REACT_APP_R2_ACCESS_KEY_ID!;
const secretAccessKey = process.env.REACT_APP_R2_SECRET_ACCESS_KEY!;
const endpoint = process.env.REACT_APP_R2_ENDPOINT!;
const bucket = process.env.REACT_APP_R2_BUCKET!;

const s3 = new AWS.S3({
    accessKeyId,
    secretAccessKey,
    endpoint: new AWS.Endpoint(endpoint),
    region: 'auto',
    signatureVersion: 'v4',
});

const deleteImageFromR2 = async (tileId: number): Promise<void> => {
    const fileName = `tile-${tileId}.png`;
    try {
        await s3
            .deleteObject({
                Bucket: bucket,
                Key: fileName,
            })
            .promise();
        console.log(`🗑️ 删除成功: ${fileName}`);
    } catch (error) {
        console.warn(`⚠️ 删除失败或无文件: ${fileName}`, error);
    }
};

const uploadImageToR2 = async (file: File, tileId: number): Promise<string> => {
    const fileName = `tile-${tileId}.png`;

    // ✅ 上传前尝试删除已有图片
    await deleteImageFromR2(tileId);

    await s3
        .putObject({
            Bucket: bucket,
            Key: fileName,
            Body: file,
            ContentType: file.type,
            ACL: 'public-read',
        })
        .promise();

    console.log(`✅ 上传成功: ${fileName}`);
    return fileName;
};

export default uploadImageToR2;
export { deleteImageFromR2 };
