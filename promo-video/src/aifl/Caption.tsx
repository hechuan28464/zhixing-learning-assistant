import { useVisualTheme, sceneDefaults } from '../themes/visual-theme';
import { interpolate, useCurrentFrame } from 'remotion';


/** Context-level defaults, editable per clip in the workbench (hex = sRGB of the oklch tokens). */
export const CAPTION_DEFAULTS = {
  bottom: 72,
  fontSize: 60, // Q11：镜头叙事字幕有效字高 ≥56px（1080p 取 60 档）
  color: '#748381',  // 知行伴学 --text-muted
  accent: '#225e59', // 知行伴学 --brand-teal
};

/** Screen-space narration caption: a mono UI info-strip at the bottom of the
 * frame, led by a small amber square. Fades/rises in over 8 frames and fades
 * out over the last 8 of its window. */
export const Caption: React.FC<{
  text: string;
  duration: number;
  bottom?: number;
  fontSize?: number;
  color?: string;
  accent?: string;
}> = (props) => {
  const theme = useVisualTheme();
  const paperStyle = theme.id === 'ink-press';
  const MONO = (paperStyle ? '"Segoe UI Variable", "Microsoft YaHei", sans-serif' : theme.font);
  const {text, duration, ...style} = props;
  const {fontSize, color, accent, bottom} = {...sceneDefaults(theme, 'caption', CAPTION_DEFAULTS), ...style};
  const frame = useCurrentFrame();
  const inT = interpolate(frame, [0, 8], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const outT = interpolate(frame, [duration - 8, duration], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        right: 0,
        bottom,
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'baseline',
        gap: 14,
        fontFamily: MONO,
        fontSize,
        letterSpacing: paperStyle ? '0.06em' : '0.015em',
        // Q11：字幕压在真实页面上，配 scrim 底板保证对比度
        ...(paperStyle
          ? { width: 'max-content', maxWidth: '86%', margin: '0 auto', padding: '12px 30px', borderRadius: 12, background: 'rgba(32,54,60,0.66)', color: '#f7f9f7', lineHeight: 1.3 }
          : { left: '50%', right: 'auto', width: 'max-content', maxWidth: '90%', padding: '8px 18px', borderRadius: 8, background: theme.surface, border: `1px solid ${theme.border}`, fontWeight: 500, lineHeight: 1.2 }),
        textTransform: 'uppercase',
        color: paperStyle ? '#f7f9f7' : color,
        opacity: inT * outT,
        transform: paperStyle ? `translateY(${(1 - inT) * 8}px)` : `translate(-50%, ${(1 - inT) * 8}px)`,
        pointerEvents: 'none',
      }}
    >
      <span style={{ width: 8, height: 8, background: paperStyle ? '#efba8f' : accent, display: 'inline-block' }} />
      <span>{text}</span>
    </div>
  );
};
