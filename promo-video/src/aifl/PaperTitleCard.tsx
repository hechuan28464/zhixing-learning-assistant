import { useVisualTheme, themePaint, sceneDefaults } from '../themes/visual-theme';
import { AbsoluteFill, interpolate, useCurrentFrame, Easing } from 'remotion';
import { DigitRoll } from './DigitRoll';


/** Context-level defaults (copy size / palette). Exposed as props so the
 * workbench can edit them per clip; the motion timing stays fixed. Hex values
 * are the sRGB renderings of the original oklch tokens. */
export const TITLE_CARD_DEFAULTS = {
  fontSize: 92,
  ink: '#20363c',    // 知行伴学 --text-main 墨蓝
  accent: '#225e59', // 知行伴学 --brand-teal 深青瓷
  muted: '#748381',  // 知行伴学 --text-muted
  paper: '#f7f9f7',  // 知行伴学 --canvas 纸白
};

/**
 * Paper title card: warm paper field, serif statement letterpressed word by
 * word, amber italic accent word, amber underline growing beneath.
 */
export const PaperTitleCard: React.FC<{
  duration: number;
  words: { text: string; accent?: boolean }[];
  sub?: string;
  subDigits?: string;
  fontSize?: number;
  ink?: string;
  accent?: string;
  muted?: string;
  paper?: string;
}> = (props) => {
  const theme = useVisualTheme();
  const paperStyle = theme.id === 'ink-press';
  const paint = (css: string) => themePaint(theme, css);
  const SERIF = paperStyle ? '"Noto Serif SC", "SimSun", serif' : theme.font;
  const MONO = (paperStyle ? '"Segoe UI Variable", "Microsoft YaHei", sans-serif' : theme.font);
  const {duration, words, sub, subDigits, ...style} = props;
  const {fontSize, ink, accent, muted, paper} = {...sceneDefaults(theme, 'title-card', TITLE_CARD_DEFAULTS), ...style};
  const frame = useCurrentFrame();
  const fadeOut = interpolate(frame, [duration - 8, duration], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const underline = interpolate(frame, [16, 34], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.bezier(0.3, 0, 0.2, 1),
  });
  const subT = interpolate(frame, [10, 22], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill
      style={{
        backgroundColor: paper,
        justifyContent: 'center',
        alignItems: 'center',
        opacity: fadeOut,
        backgroundImage: paint('radial-gradient(1100px 750px at 50% 42%, rgba(234,242,238,0.9), transparent 65%)'),
      }}
    >
      <div style={{ textAlign: 'center', maxWidth: 1500 }}>
        <div
          style={{
            fontFamily: SERIF, fontSize, fontWeight: 600, lineHeight: 1.22,
            color: ink, letterSpacing: '0.01em',
            display: 'flex', flexWrap: 'wrap', justifyContent: 'center', columnGap: '0.16em',
          }}
        >
          {words.map((w, i) => {
            const delay = 4 + i * 4;
            const t = interpolate(frame, [delay, delay + 9], [0, 1], {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
              easing: Easing.bezier(0.2, 0.75, 0.3, 1),
            });
            return (
              <span
                key={i}
                style={{
                  opacity: t,
                  transform: `scale(${1.28 - 0.28 * t})`,
                  filter: `blur(${(1 - t) * 7}px)`,
                  display: 'inline-block',
                  // 中文无真斜体：强调块改用字重+强调色，不做 faux italic
                  fontStyle: 'normal',
                  fontWeight: w.accent ? 700 : 600,
                  color: w.accent ? accent : undefined,
                }}
              >
                {w.text}
              </span>
            );
          })}
        </div>
        <div
          style={{
            height: 6, width: 220, margin: '38px auto 0', borderRadius: 3,
            background: accent, transform: `scaleX(${underline})`,
          }}
        />
        {sub ? (
          <div style={{ fontFamily: MONO, fontSize: paperStyle ? 34 : 44, letterSpacing: '0.08em', color: muted, marginTop: 34, opacity: subT, textTransform: 'uppercase', display: 'flex', justifyContent: 'center', alignItems: 'baseline', gap: '0.5em' }}>
            {subDigits ? <DigitRoll value={subDigits} delay={12} fontSize={paperStyle ? 34 : 44} color={accent} /> : null}
            <span>{sub}</span>
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};
