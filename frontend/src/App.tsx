import { MapGrid } from './components/MapGrid';
import { Palette } from './components/Palette';
import { GRID_HEIGHT, GRID_WIDTH } from './constants';
import { useMapEditor } from './hooks/useMapEditor';
import { useObjectDrag } from './hooks/useObjectDrag';

export default function App() {
  const { objects, place, move } = useMapEditor();
  const { gridRef, preview, movingId, startPlacing, startMoving } = useObjectDrag({
    objects,
    place,
    move,
  });

  return (
    <div className="min-h-screen bg-zinc-100 p-8">
      <h1 className="mb-6 text-2xl font-bold text-zinc-900">店内マップを作る</h1>
      <div className="flex items-start justify-center gap-8">
        <Palette onPickUp={startPlacing} />
        <div>
          <MapGrid
            width={GRID_WIDTH}
            height={GRID_HEIGHT}
            objects={objects}
            preview={preview}
            movingId={movingId}
            gridRef={gridRef}
            onObjectPointerDown={startMoving}
          />
          <p className="mt-3 text-sm">
            {preview && !preview.valid ? (
              <span className="font-bold text-red-700">ここには置けません</span>
            ) : (
              <span className="text-zinc-600">
                置いたものは、ドラッグでいつでも動かせます
              </span>
            )}
          </p>
        </div>
      </div>
    </div>
  );
}
