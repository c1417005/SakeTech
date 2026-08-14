import { CELL_SIZE } from '../constants';

type MapGridProps = {
  width: number;
  height: number;
};

// 方眼は背景。セルを DOM 要素として並べず、罫線をグラデーションで描く。
const LINE_COLOR = '#d4d4d8';

export function MapGrid({ width, height }: MapGridProps) {
  return (
    <div
      className="border-2 border-zinc-400 bg-white"
      style={{
        width: width * CELL_SIZE,
        height: height * CELL_SIZE,
        backgroundImage: `linear-gradient(to right, ${LINE_COLOR} 1px, transparent 1px), linear-gradient(to bottom, ${LINE_COLOR} 1px, transparent 1px)`,
        backgroundSize: `${CELL_SIZE}px ${CELL_SIZE}px`,
      }}
    />
  );
}
