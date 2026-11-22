import { useVisualTheme, themePaint, themeAsset } from '../themes/visual-theme';
import { AbsoluteFill, Audio, Sequence, interpolate, staticFile, useCurrentFrame } from 'remotion';
import { SceneOpen } from './live/SceneOpen';
import { SceneFlyIn } from './live/SceneFlyIn';
import { SceneDetail } from './live/SceneDetail';
import { ScenePapers } from './live/ScenePapers';
import { SceneWbr } from './live/SceneWbr';
import { PaperTitleCard } from './PaperTitleCard';
import { SceneOutroLive } from './live/SceneOutroLive';
import { FlashCut } from './FlashCut';
import { Caption } from './Caption';

// ~36s @ 30fps — paper-and-ink morning reading room (10 shots). Both wordmark
// moments (brand open, outro sign-off) hold a full second once fully on.
// 卡拍：BGM = Freesound fs-629161（90.004 BPM，拟合 T=0.66664s = 20.0f/拍，
// 相位 t0=1.2f）。所有切点按 20f 拍网重排，逐一落在整数拍上。
export const AIFL_SHOTS = {
  morning: { from: 0, duration: 220 },   // 0–7.3s   brand ~46f + 30f hold + 138f macro   (0 拍)
  card1: { from: 220, duration: 60 },    // 7.3–9.3s "数学、编程、阅读，一个空间里学。"     (11 拍)
  table: { from: 280, duration: 200 },   // 9.3–16.0s pile close-up → deal → scroll → search → filter → click (14 拍)
  macro: { from: 480, duration: 100 },   // 16.0–19.3s macro card detail, rows reveal      (24 拍)
  card2: { from: 580, duration: 60 },    // 19.3–21.3s "证据，而不是一个总分。"              (29 拍)
  chart: { from: 640, duration: 100 },   // 21.3–24.7s 学习动态 stack + counter             (32 拍)
  cardWbr: { from: 740, duration: 60 },  // 24.7–26.7s "每一次作答，留下可核查的依据。"      (37 拍)
  wbr: { from: 800, duration: 100 },     // 26.7–30.0s 真实导师对话 block by block reveal   (40 拍)
  card3: { from: 900, duration: 60 },    // 30.0–32.0s "下一步，有依据地继续。"              (45 拍)
  outro: { from: 960, duration: 120 },   // 32.0–36.0s defocus + letterpress sign-off (+1s hold) (48 拍)
} as const; // sum = 1080 = 54 拍

export const AIFL_TOTAL = 1080;

// title-card copy: space-separated words, `*word*` = accent italic word. Single
// source for the render below and for the workbench manifest (workbench.ts).
// 中文按语义块空格分词（parseWords 以空格切），强调块用 *…* 标出。
export const TITLE_CARDS = {
  card1: { text: '数学、编程、阅读， *一个* 空间里学。' },
  card2: { text: '*证据* ，而不是一个总分。', sub: '道题，判题由确定性契约完成', subDigits: '39' },
  cardWbr: { text: '每一次作答， *留下* 可核查的依据。' },
  card3: { text: '下一步， *有依据* 地继续。' },
} as const;

export const parseWords = (text: string): { text: string; accent?: boolean }[] =>
  text
    .split(/\s+/)
    .filter(Boolean)
    .map((w) => {
      const m = w.match(/^\*(.+)\*$/);
      return m ? { text: m[1], accent: true } : { text: w };
    });

// warm flash cuts straddle these hard cuts (from = cut − 5, 10f long)
export const FLASH_CUTS = [AIFL_SHOTS.table.from, AIFL_SHOTS.macro.from, AIFL_SHOTS.chart.from, AIFL_SHOTS.wbr.from];

// keyboard windows sized to the on-screen action (S4 拟音与动作等长):
// search typing = 2 chars × 3f from abs 403 → 8f window; wbr block reveals end
// at abs ≈806 → 26f window from 781. Derivation recorded in
// out/qa/review/audio-offset.md.
export const sfxDuration = (s: { from: number; src: string }) =>
  s.src === 'sfx/fs-447909.mp3' ? (s.from > 700 ? 26 : 8) : 90;

// bottom-strip narration over the live shots (absolute frames; outro stays clean)
export const CAPTIONS = [
  { from: 90, duration: 40, text: '三门课程 · 九篇自编讲义' },
  // (the hero-card hover annotation lives inside SceneOpen as a 3D floating note)
  { from: 323, duration: 44, text: '按题族区分独立、受助与重复' },
  { from: 400, duration: 55, text: '搜索 · 筛选 · 打开' },
  { from: 492, duration: 68, text: '独立表现 · 帮助程度 · 目标覆盖 · 保持' },
  { from: 653, duration: 72, text: '每一次行动，都会留下来' },
  { from: 814, duration: 78, text: '回答可核查 · 学习状态以任务证据为准' },
] as const;

// sound design pinned to animation beats. Sources: Freesound CC0 previews,
// selected per references/sfx-sourcing.md. Pins compensate each file's measured
// onset/energy-peak latency (public/audio/sfx/audio-manifest.json): percussive
// one-shots pin their energy peak on the action frame, beds pin active_start,
// the riser pins its peak on the wordmark stamp (978). See
// out/qa/review/audio-offset.md for the measured table.
export const SFX: { from: number; src: string; volume: number }[] = [
  // brand open: soft transition as the lockup lands, whoosh into the console
  { from: 10, src: 'sfx/fs-742833.mp3', volume: 0.41 },
  { from: 73, src: 'sfx/fs-585257.mp3', volume: 0.81 }, // brand → dashboard
  // hero card: whoosh up on the pop, sparkle on the beam scan, impact reseat
  { from: 124, src: 'sfx/fs-486234.mp3', volume: 0.86 },
  { from: 141, src: 'sfx/fs-545238.mp3', volume: 0.33 },
  { from: 199, src: 'sfx/fs-786514.mp3', volume: 0.82 },
  // title cards ride a quick swoosh (peak pinned on the card's first frame = cut)
  { from: 202, src: 'sfx/fs-779808.mp3', volume: 0.36 }, // card1 @220
  // deck shot: soft transition into the pile close-up, whoosh as the orbit
  // pulls back and dealing starts, fast whooshes as the deal accelerates,
  // then the scroll rest → big whoosh back up to the search bar
  { from: 280, src: 'sfx/fs-742833.mp3', volume: 0.41 }, // pile close-up
  { from: 310, src: 'sfx/fs-486234.mp3', volume: 0.86 }, // pull-back + first deals
  { from: 340, src: 'sfx/fs-585257.mp3', volume: 0.72 }, // dealing accelerates
  { from: 356, src: 'sfx/fs-585257.mp3', volume: 0.58 }, // full flurry
  { from: 390, src: 'sfx/fs-486234.mp3', volume: 0.86 }, // swoosh back to header
  // typing (3f/char) + a breath + filter + click
  { from: 406, src: 'sfx/fs-447909.mp3', volume: 0.25 }, // trimmed to the typing
  { from: 435, src: 'sfx/fs-585257.mp3', volume: 0.72 }, // grid filters away
  { from: 453, src: 'sfx/fs-270435.mp3', volume: 0.5 }, // click on the result card
  { from: 442, src: 'sfx/fs-779808.mp3', volume: 0.32 }, // push-in
  // detail rows embed with one cinematic transition sweep
  { from: 488, src: 'sfx/fs-742833.mp3', volume: 0.46 },
  { from: 562, src: 'sfx/fs-779808.mp3', volume: 0.36 }, // card2 @580
  // papers stack: soft transition, camera-click as the counter settles
  { from: 641, src: 'sfx/fs-742833.mp3', volume: 0.41 },
  { from: 665, src: 'sfx/fs-270435.mp3', volume: 0.38 },
  { from: 722, src: 'sfx/fs-779808.mp3', volume: 0.36 }, // cardWbr @740
  // wbr: the conversation "writes itself" over live keyboard typing, then the
  // two rails wipe on stage (soft transitions on each wipe)
  { from: 802, src: 'sfx/fs-742833.mp3', volume: 0.41 },
  { from: 806, src: 'sfx/fs-447909.mp3', volume: 0.21 }, // trimmed to the writing reveals
  { from: 844, src: 'sfx/fs-742833.mp3', volume: 0.33 }, // left rail wipes on
  { from: 852, src: 'sfx/fs-742833.mp3', volume: 0.29 }, // right rail wipes on
  { from: 882, src: 'sfx/fs-779808.mp3', volume: 0.36 }, // card3 @900
  // outro: riser builds across the cut and peaks on the wordmark stamp (998),
  // impact peak pinned to the same stamp, sparkle on the rule + tagline glint
  { from: 916, src: 'sfx/fs-685256.mp3', volume: 1.5 },
  { from: 974, src: 'sfx/fs-541029.mp3', volume: 0.82 },
  { from: 1025, src: 'sfx/fs-545238.mp3', volume: 0.28 }, // rule + tagline glint
];

// BGM bed: Freesound fs-629161 "Spacey Lofi Loop 90 BPM" (CC0). 90.004 BPM,
// measured T=0.66664s (=20.0f/beat) and t0=1.2f, so the head is trimmed 1f and
// every cut sits on an integer beat. Kept low under the SFX; ducks at the
// wordmark stamp (960–990), fades in over the brand open and out at the tail.
const BGM_SRC = 'audio/bgm/fs-629161.mp3';
const BGM_BASE = 0.55;
const BgmBed: React.FC = () => {
  const f = useCurrentFrame();
  const gain = interpolate(
    f,
    [0, 28, 940, 960, 990, 1044, 1080],
    [0, BGM_BASE, BGM_BASE * 1.1, BGM_BASE * 1.12, BGM_BASE * 0.84, BGM_BASE * 0.84, 0],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' },
  );
  return <Audio src={staticFile(BGM_SRC)} startFrom={3} endAt={1080} volume={gain} />;
};

export const AiflMain: React.FC<{ bgm?: boolean }> = ({ bgm = true }) => {
  const theme = useVisualTheme();
  const paint = (css: string) => themePaint(theme, css);
  const asset = (src: string) => themeAsset(theme, src);

  return (
    <AbsoluteFill style={{ backgroundColor: paint('#f2eee6') }}>
      {/* optional music bed, switched by the `bgm` input prop so both the
          with-BGM and SFX-only versions render from this one timeline */}
      {bgm ? <BgmBed /> : null}
      {/* beat-pinned promo sound effects (no music bed — SFX only) */}
      {SFX.map((s, i) => (
        <Sequence
          key={`sfx-${i}`}
          from={s.from}
          durationInFrames={sfxDuration(s)}
        >
          <Audio src={asset(`audio/${s.src}`)} volume={s.volume} />
        </Sequence>
      ))}
      <Sequence from={AIFL_SHOTS.morning.from} durationInFrames={AIFL_SHOTS.morning.duration}>
        <SceneOpen />
      </Sequence>
      <Sequence from={AIFL_SHOTS.card1.from} durationInFrames={AIFL_SHOTS.card1.duration}>
        <PaperTitleCard
          duration={AIFL_SHOTS.card1.duration}
          words={parseWords(TITLE_CARDS.card1.text)}
        />
      </Sequence>
      <Sequence from={AIFL_SHOTS.table.from} durationInFrames={AIFL_SHOTS.table.duration}>
        <SceneFlyIn />
      </Sequence>
      <Sequence from={AIFL_SHOTS.macro.from} durationInFrames={AIFL_SHOTS.macro.duration}>
        <SceneDetail />
      </Sequence>
      <Sequence from={AIFL_SHOTS.card2.from} durationInFrames={AIFL_SHOTS.card2.duration}>
        <PaperTitleCard
          duration={AIFL_SHOTS.card2.duration}
          words={parseWords(TITLE_CARDS.card2.text)}
          sub={TITLE_CARDS.card2.sub}
          subDigits={TITLE_CARDS.card2.subDigits}
        />
      </Sequence>
      <Sequence from={AIFL_SHOTS.chart.from} durationInFrames={AIFL_SHOTS.chart.duration}>
        <ScenePapers />
      </Sequence>
      <Sequence from={AIFL_SHOTS.cardWbr.from} durationInFrames={AIFL_SHOTS.cardWbr.duration}>
        <PaperTitleCard
          duration={AIFL_SHOTS.cardWbr.duration}
          words={parseWords(TITLE_CARDS.cardWbr.text)}
        />
      </Sequence>
      <Sequence from={AIFL_SHOTS.wbr.from} durationInFrames={AIFL_SHOTS.wbr.duration}>
        <SceneWbr />
      </Sequence>
      <Sequence from={AIFL_SHOTS.card3.from} durationInFrames={AIFL_SHOTS.card3.duration}>
        <PaperTitleCard
          duration={AIFL_SHOTS.card3.duration}
          words={parseWords(TITLE_CARDS.card3.text)}
        />
      </Sequence>
      <Sequence from={AIFL_SHOTS.outro.from} durationInFrames={AIFL_SHOTS.outro.duration}>
        <SceneOutroLive />
      </Sequence>
      {/* narration captions over the live shots (under the flash cuts) */}
      {CAPTIONS.map((c) => (
        <Sequence key={c.from} from={c.from} durationInFrames={c.duration}>
          <Caption text={c.text} duration={c.duration} />
        </Sequence>
      ))}
      {/* warm flash cuts straddling scene changes */}
      {FLASH_CUTS.map((cut) => (
        <Sequence key={cut} from={cut - 5} durationInFrames={10}>
          <FlashCut duration={10} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
