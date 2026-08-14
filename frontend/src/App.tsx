import { MapGrid } from './components/MapGrid';
import { GRID_HEIGHT, GRID_WIDTH } from './constants';

export default function App() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-100">
      <MapGrid width={GRID_WIDTH} height={GRID_HEIGHT} />
    </div>
  );
}
