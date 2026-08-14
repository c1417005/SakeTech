import { CELL_SIZE } from '../constants';
import type { PlacementPreview } from '../hooks/useObjectDrag';
import type { MapObject } from '../types/map';
import { PlacedObject } from './PlacedObject';

type MapGridProps = {
  width: number;
  height: number;
  objects: MapObject[];
  preview: PlacementPreview | null;
  movingId: string | null;
  /** 座標計算の基準。枠線を含まない、ちょうど方眼の大きさの層を指す。 */
  gridRef: React.RefObject<HTMLDivElement | null>;
  onObjectPointerDown: (event: React.PointerEvent, object: MapObject) => void;
};

// 方眼は背景。セルを DOM 要素として並べず、罫線をグラデーションで描く。
const LINE_COLOR = '#d4d4d8';

export function MapGrid({
  width,
  height,
  objects,
  preview,
  movingId,
  gridRef,
  onObjectPointerDown,
}: MapGridProps) {
  return (
    <div className="inline-block border-2 border-zinc-400 bg-white">
      <div
        ref={gridRef}
        className="relative touch-none"
        style={{
          width: width * CELL_SIZE,
          height: height * CELL_SIZE,
          // 1枚の画像を作り、敷き詰める
          backgroundImage: `linear-gradient(to right, ${LINE_COLOR} 1px, transparent 1px), linear-gradient(to bottom, ${LINE_COLOR} 1px, transparent 1px)`,
          backgroundSize: `${CELL_SIZE}px ${CELL_SIZE}px`,
        }}
      >
        {objects.map((object) => (
          <PlacedObject
            key={object.id}
            object={object}
            appearance={object.id === movingId ? 'moving' : 'placed'}
            onPointerDown={(event) => onObjectPointerDown(event, object)}
          />
        ))}
        {preview && (
          <PlacedObject
            object={preview.object}
            appearance={preview.valid ? 'preview-ok' : 'preview-ng'}
          />
        )}
      </div>
    </div>
  );
}
