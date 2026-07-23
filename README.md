# Yoyo String Annotation 标签说明

`yoyo-string-annotation` 从视频中分散采样帧，由视觉 agent 标注悠悠球、绳线、手部、场景和绳线路径，并经过审核后导出可训练数据。当前逐帧标签 schema 为 `agent_yoyo_string_annotation_v3`。

## 训练标签总览

| 标签 | 类型 | 取值或格式 | 主要用途 |
| --- | --- | --- | --- |
| `string_visibility` | 分类 | `visible`、`partial`、`not_visible`、`uncertain` | 绳线正负样本和可见性判断 |
| `string_polylines_pixel` | 几何 | 多段 `[[x,y], ...]` 中心线 | 绳线分割、中心线检测 |
| `string_mask_polygons_pixel` | 几何 | 多个 `[[x,y], ...]` 多边形 | 绳线像素分割 |
| `visibility` | 分类 | `visible`、`partially_visible`、`occluded`、`out_of_frame`、`absent`、`uncertain` | 悠悠球可见性 |
| `yoyo_bbox_pixel` | 几何 | `[x1,y1,x2,y2]` | 悠悠球位置辅助标签 |
| `hands_pixel` | 关键点 | `left`、`right` 各为 `[x,y]` 或 `null` | 手部位置和绳线端点关系 |
| `string_attachment_class` | 分类 | `hand_and_yoyo_attached`、`yoyo_detached`、`hand_detached`、`unknown` | 绳线连接关系 |
| `scene_label` | 分类 | `trick`、`transition`、`non_trick`、`unknown` | 当前画面是否处于招式 |
| `trick_orientation` | 分类 | `normal`、`horizontal`、`unknown`、`not_applicable` | 招式投掷方向 |
| `variation_tags` | 多标签 | 开放字符串列表 | 形态、难例和数据分层 |
| `string_path` | 结构化路径 | 路径、锚点、边证据、置信度 | 绳线连续性和拓扑辅助任务 |
| `bad_case` | 多标签 | 开放字符串列表 | 模糊、遮挡、传播失败等难例 |

所有主要像素坐标还会生成 `0-999` 范围的归一化镜像，例如 `yoyo_bbox_2d`、`string_polylines_2d` 和 `hands_2d`。原始像素坐标是权威数据。

## 绳线训练真值

绳线分割是当前 skill 的主要训练目标。

### 可见性

- `visible`：主要可见绳线可以可靠标注，必须包含中心线或掩码。
- `partial`：只能可靠标注部分可见绳线，必须包含当前帧中确实可见的几何。
- `not_visible`：没有可确认的绳线像素，作为空掩码负样本，不保留绳线几何。
- `uncertain`：无法确定正负，不进入训练集。

### 几何

- `string_polylines_pixel`：一条或多条绳线中心线。发生遮挡或无法确认的交叉时必须拆成多段。
- `string_mask_polygons_pixel`：可选的绳线区域多边形。只有两侧边界都能可靠判断时使用。
- 当只有中心线时，下游可使用固定的小宽度将其栅格化为分割掩码。

只允许将当前帧中可见并经过审核的几何作为分割真值，不应跨越遮挡区域补画绳线。

## 悠悠球与手部标签

`visibility` 描述悠悠球当前可见状态；`yoyo_bbox_pixel` 记录可见悠悠球主体的边界框。`hands_pixel` 分别记录左右手关键点，缺失或无法判断时为 `null`。

这些字段主要用于绳线端点检查、关系建模和后续多任务训练。当前导出门控以绳线审核状态为主，不能默认把 `yoyo_bbox_pixel` 当成已经独立审核完成的目标检测真值。

## 场景与招式标签

### `scene_label`

- `trick`：正在进行招式。
- `transition`：招式之间的准备、调整或移动。
- `non_trick`：当前不是招式画面。
- `unknown`：无法判断。

当前 `scene_label` 不区分进场和离场，也不记录完整表演阶段。

### `trick_orientation`

- `normal`：常规向下或明显非水平的投掷方向。
- `horizontal`：经相邻帧确认的水平投掷方向。
- `unknown`：缺少足够时序证据。
- `not_applicable`：`scene_label=non_trick` 时使用。

当前不会记录具体招式名称，例如 Sleeper、Trapeze 或其他招式类别。

## 绳线路径结构

`string_path` 描述绳线的有序路径和连续性，不等同于分割掩码。

- `topology`：`open`、`loop`、`branched`、`multiple`、`uncertain`。
- `reconstruction_status`：`complete`、`partial`、`uncertain`、`not_applicable`。
- `start_anchor` / `end_anchor`：`left_hand`、`right_hand`、`yoyo`、`unknown`。
- `evidence`：`observed`、`temporal`、`inferred`。
- `confidence`：每条连续边的 `0-1` 置信度。
- `unresolved_gaps`：遮挡或无法确定的路径缺口。

只有 `observed` 边对应的当前帧可见几何可以进入分割真值。`temporal` 和 `inferred` 仅用于时序连续性、拓扑分析和复核。

## 变化与难例标签

`variation_tags` 是开放多标签字段，常见值包括：

```text
straight, curved, v_shape, loop, crossing, branched,
multi_segment, occluded, motion_blur, low_contrast,
edge_clipped, small_yoyo, no_string, background_edge
```

`bad_case` 记录当前样本的问题，例如部分遮挡、无法可靠传播或绳线不可见。两者适合用于采样平衡、难例挖掘和评估分层，不直接表示像素真值。

## 训练集纳入规则

只有满足以下条件的记录可以进入审核后的绳线训练集合：

1. `string_review_status` 为 `approved` 或 `reviewed`。
2. `visible` / `partial` 样本包含有效中心线或掩码。
3. `not_visible` 样本不包含绳线几何，并作为负样本使用。
4. `uncertain`、`unresolved`、`rejected` 和待审核记录全部排除。
5. `temporal` 和 `inferred` 路径边不栅格化为分割真值。
6. 后续划分必须以完整 `source_group` 为单位，禁止同一来源视频跨 train、val 和 test。

## 溯源与审核元数据

以下字段随标签保存，但不是训练类别：

- 视频溯源：`source_video`、`source_video_sha256`、`source_group`、`video_id`。
- 帧位置：`frame_index`、`timestamp_s`、`sequence_id`、`sampling_role`、`anchor_frame_index`。
- 图片身份：`source_image`、`image_sha256`、`image_size`。
- 审核状态：`review_status`、`bbox_review_status`、`string_review_status`。
- 质量记录：`quality.revision`、`quality.history`、`quality.reviews`。

`sampling_role` 只表示采样用途：`anchor` 是分散采样锚点，`temporal_context` 是锚点附近的时序参考帧，不是人物角色。

## 当前没有记录的标签

- 人物姓名、`subject_id` 或选手身份。
- 具体招式名称或招式类别。
- `entrance`、`preparation`、`performance`、`exit` 等完整表演阶段。
- `train`、`val`、`test` 数据集划分。

如需人物隔离或进出场识别，应在后续 schema 中增加独立字段，不能从 `sampling_role` 或现有 `scene_label` 推断。

## 标签示例

```json
{
  "source_video": "videos/example.mp4",
  "source_video_sha256": "0000000000000000000000000000000000000000000000000000000000000000",
  "source_group": "example-a1b2c3d4e5",
  "video_id": "example-a1b2c3d4e5",
  "frame_index": 1250,
  "timestamp_s": 25.0,
  "sampling_role": "anchor",
  "visibility": "visible",
  "yoyo_bbox_pixel": [742, 430, 790, 480],
  "string_visibility": "partial",
  "string_polylines_pixel": [
    [[510, 190], [548, 250], [602, 318]],
    [[635, 340], [700, 397], [754, 440]]
  ],
  "string_mask_polygons_pixel": null,
  "hands_pixel": {"left": [510, 190], "right": null},
  "string_attachment_class": "hand_and_yoyo_attached",
  "scene_label": "trick",
  "trick_orientation": "horizontal",
  "variation_tags": ["occluded", "curved", "multi_segment"],
  "string_review_status": "approved"
}
```

<img width="1282" height="3566" alt="4355f46e9582de9cb010f98bf033a539" src="https://github.com/user-attachments/assets/448cbc80-9cf7-4ba3-9a58-0fdbd4539473" />

