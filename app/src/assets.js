import {iconAssets} from './iconAssets.js'
// All product art is managed here. Reuse these URLs instead of ad hoc screenshots.
export const artwork = Object.freeze({
  logo: '/assets/access-v1/logo-path.webp',
  sidebar: '/assets/competition-v1/common/sidebar.png.webp',
  hero: '/assets/competition-v1/home/hero.png.webp',
  mathematics: '/assets/competition-v1/home/course-math.png.webp',
  programming: '/assets/competition-v1/home/course-code.png.webp',
  reading: '/assets/competition-v1/home/course-reading.png.webp',
  mentor: '/assets/access-v1/mentor-compact.webp',
  learner: '/assets/access-v1/learner-compact.webp',
  systems: '/assets/access-v1/recommend-systems-compact.webp',
  city: '/assets/access-v1/recommend-city-compact.webp',
  curiosity: '/assets/access-v1/recommend-question-compact.webp',
  growth: '/assets/competition-v1/scenes/growth-botanical.png.webp',
  growthQuote: '/assets/backgrounds/banner-growth-with-quote.png.webp',
})

export const icon = (name, variant = 'teal') => name==='play'?`/assets/video-learning/icons/nav-play-${variant==='white'?'white':'teal'}.svg`:iconAssets[variant+'/'+name] || `/assets/competition-v1/icons/${variant}/${name}.svg`
