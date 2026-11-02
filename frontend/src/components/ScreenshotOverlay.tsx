import type { ScanResult } from "../types";
import { SEV_STYLE } from "../ui";
import { shotUrl } from "../api";

const VW = 1280;
const VH = 800;

export default function ScreenshotOverlay({
  scan,
  selectedId,
  onSelect,
}: {
  scan: ScanResult;
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const src = shotUrl(scan.screenshot_path);
  if (!src) return null;
  const visible = scan.findings.filter((f) => f.bbox);
  return (
    <figure className="rounded-xl border border-slate-800 bg-slate-900/60 p-3">
      <figcaption className="mb-2 flex items-center justify-between text-xs text-slate-400">
        <span>Page screenshot (top of page) — click a box to inspect an issue</span>
        <span>{visible.length} highlighted</span>
      </figcaption>
      <div className="relative w-full overflow-hidden rounded-lg bg-white" style={{ aspectRatio: `${VW} / ${VH}` }}>
        <img src={src} alt={`Screenshot of ${scan.url}`} className="absolute inset-0 h-full w-full object-fill" />
        {visible.map((f) => {
          const b = f.bbox!;
          const sel = f.id === selectedId;
          return (
            <button
              key={f.id}
              onClick={() => onSelect(f.id)}
              title={`${f.severity}: ${f.rule_id}`}
              aria-label={`${f.severity} issue ${f.rule_id}`}
              className="absolute"
              style={{
                left: `${(b.x / VW) * 100}%`,
                top: `${(b.y / VH) * 100}%`,
                width: `${Math.max((b.w / VW) * 100, 0.8)}%`,
                height: `${Math.max((b.h / VH) * 100, 1)}%`,
                border: `${sel ? 3 : 2}px solid ${SEV_STYLE[f.severity].box}`,
                background: sel ? `${SEV_STYLE[f.severity].box}55` : `${SEV_STYLE[f.severity].box}1f`,
                zIndex: sel ? 10 : 1,
              }}
            />
          );
        })}
      </div>
    </figure>
  );
}
