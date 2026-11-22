"""Collect independent production assets; review files remain outside public/."""
import hashlib
import html
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'app'
PUBLIC = APP / 'public'
DEST = PUBLIC / 'assets/competition-v1'
DESIGN = APP / 'design/competition-asset-library'

ART = [
 ('logo','brand/logo-open-book.png','common/logo.png',['home','lesson','citation','settings','pbl'],'书本Logo'),
 ('sidebar','backgrounds/sidebar-mountains.png','common/sidebar.png',['home','lesson','citation','settings','pbl'],'导航山峰背景'),
 ('mentor','avatars/mentor-linzhi.png','common/mentor.png',['home','lesson','citation','settings','pbl'],'原林知头像'),
 ('learner','avatars/learner-avatar.png','common/learner.png',['home','lesson','citation','settings','pbl'],'学习者头像'),
 ('homeHero','illustrations/hero-connected-learning.png','home/hero.png',['home'],'首页书本与轨道球主图'),
 ('mathCourse','courses/course-mathematics.png','home/course-math.png',['home'],'数学课程封面'),
 ('readingCourse','courses/course-reading.png','home/course-reading.png',['home'],'阅读课程封面'),
 ('codeCourse','courses/course-programming.png','home/course-code.png',['home'],'编程课程封面'),
 ('customGoal','recommendations/recommend-systems.png','home/custom-goal.png',['home'],'开放目标拱门配图'),
 ('recommendSystems','recommendations/recommend-systems.png','home/recommend-systems.png',['home'],'推荐系统思维缩略图'),
 ('recommendCity','recommendations/recommend-city.png','home/recommend-city.png',['home'],'推荐城市数学缩略图'),
 ('recommendQuestion','recommendations/recommend-curiosity.png','home/recommend-question.png',['home'],'推荐提问缩略图'),
 ('growthOriginal','backgrounds/banner-growth.png','home/growth-original.png',['home'],'原版成长配图备用'),
 ('lessonScene','feature-pages/scenes/lesson-scene.png','lesson/scene.png',['lesson'],'课时场景原分离图'),
 ('lessonBook','split-elements/elements/knowledge-core.png','lesson/book.png',['lesson'],'独立书本元素'),
 ('lessonBridge','split-elements/elements/lesson-bridge.png','lesson/bridge.png',['lesson'],'独立石桥元素'),
 ('tutorEmpty','split-elements/elements/buddy-empty-arch.png','lesson/tutor-empty.png',['lesson'],'无对话状态拱门元素'),
 ('quoteLeaves','split-elements/elements/discussion-quote-leaves.png','citation/quote-leaves.png',['citation'],'引文卡叶片'),
 ('discussionMountains','split-elements/scenes/discussion-mountain-background.png','citation/mountains.png',['citation'],'讨论区山景背景'),
 ('discussionTerrace','split-elements/elements/discussion-paper-terrace.png','citation/terrace.png',['citation'],'独立纸张平台'),
 ('discussionLamp','split-elements/elements/buddy-lamp.png','citation/lamp.png',['citation'],'独立台灯'),
 ('discussionBooks','split-elements/elements/library-books.png','citation/books.png',['citation'],'独立书堆'),
 ('discussionCups','split-elements/elements/buddy-cups.png','citation/cups.png',['citation'],'独立杯子'),
 ('readerMagnifier','split-elements/elements/reading-magnifier.png','citation/magnifier.png',['citation'],'原文阅读放大镜'),
 ('settingsScene','feature-pages/scenes/settings-scene.png','settings/scene.png',['settings'],'设置页齿轮花草场景'),
 ('settingsGear','split-elements/elements/settings-gear.png','settings/gear.png',['settings'],'独立齿轮'),
 ('settingsDial','split-elements/elements/settings-dial.png','settings/dial.png',['settings'],'独立表盘'),
 ('settingsData','split-elements/elements/settings-data-box.png','settings/data-box.png',['settings'],'导出资料盒配图'),
 ('projectLaptop','split-elements/elements/coding-laptop.png','pbl/laptop.png',['pbl'],'独立编程笔记本'),
 ('projectBooks','split-elements/elements/library-books.png','pbl/books.png',['pbl'],'独立项目书堆'),
]
NEW = [('growthBotanical','scenes/growth-botanical.png',['home'],'成长植物新分离场景'),
       ('lessonBanner','scenes/lesson-book-bridge.png',['lesson'],'v3课时书本石桥新分离横图'),
       ('projectBanner','scenes/pbl-arch-banner.png',['pbl'],'项目页拱门书堆新分离横图')]
GLYPHS = {
 'target':'<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
 'headphones':'<path d="M3 14v-3a9 9 0 0 1 18 0v3"/><rect x="2" y="12" width="5" height="9" rx="2"/><rect x="17" y="12" width="5" height="9" rx="2"/>',
 'layers':'<path d="m12 3 10 6-10 6L2 9Z"/><path d="m2 13 10 6 10-6M2 17l10 6 10-6"/>',
 'alert-circle':'<circle cx="12" cy="12" r="9"/><path d="M12 7v6M12 17h.01"/>',
 'check-circle':'<circle cx="12" cy="12" r="9"/><path d="m7 12 3 3 7-7"/>',
 'flag':'<path d="M4 22V3c5-4 10 4 16 0v12c-6 4-11-4-16 0"/>',
 'history':'<path d="M3 11a9 9 0 1 1 2.7 7M3 5v6h6M12 7v5l3 2"/>',
 'chevron-down':'<path d="m6 9 6 6 6-6"/>',
}


def main():
    DESIGN.mkdir(parents=True, exist_ok=True)
    manifest=[];mapping={}
    def add(key,path,pages,label,status,source):
        raw=path.read_bytes()
        url='/'+path.relative_to(PUBLIC).as_posix()
        manifest.append(dict(id=key,label=label,url=url,pages=pages,status=status,source=source,
                             bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
        mapping[key]=url
    for key,relative,output,pages,label in ART:
        source=PUBLIC/'assets'/relative;target=DEST/output;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,target)
        add(key,target,pages,label,'reused_independent_original',source.relative_to(APP).as_posix())
    missing=[]
    for key,relative,pages,label in NEW:
        path=DEST/relative
        if path.exists():add(key,path,pages,label,'new_imagegen_extraction','approved_final_preview')
        else:missing.append(key)
    for variant in ['teal','white']:
        for source in sorted((PUBLIC/'assets/icons'/variant).glob('*.svg')):
            target=DEST/'icons'/variant/source.name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
            add('icon-'+variant+'-'+source.stem,target,['home','lesson','citation','settings','pbl'],source.stem+'图标（'+variant+'）','reused_native_svg',source.relative_to(APP).as_posix())
        for key,body in GLYPHS.items():
            target=DEST/'icons'/variant/(key+'.svg');target.parent.mkdir(parents=True,exist_ok=True)
            color='#225e59' if variant=='teal' else '#ffffff'
            target.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="'+color+'" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">'+body+'</svg>',encoding='utf-8')
            add('icon-'+variant+'-'+key,target,['lesson','pbl'],key+'图标（'+variant+'）','native_svg_component','project SVG geometry matching existing icon set')
    report=dict(scope='five accepted views; lesson v3 only',old_lesson_preview_used=False,review_library_public=False,
                private_statistics_removed=True,assets=manifest,missing_new_images=missing,
                total_files=len(manifest),raster_files=sum(m['url'].endswith('.png') for m in manifest),
                svg_files=sum(m['url'].endswith('.svg') for m in manifest),
                component_regions=['按钮、输入框、标签、证据卡、状态点、选项、消息气泡、段落高亮、表格、标签页均为可交互HTML/CSS组件，不烘焙进截图'])
    (DESIGN/'素材核对清单.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (APP/'src/competitionArtwork.js').write_text('// Approved independent assets; no preview screenshots.\nexport const competitionArtwork = Object.freeze('+json.dumps(mapping,ensure_ascii=False,indent=2)+')\nexport const competitionIcon = (name,variant="teal") => `/assets/competition-v1/icons/${variant}/${name}.svg`\n',encoding='utf-8')
    cards=[]
    for item in manifest:
        src='../../public'+item['url']
        cards.append('<figure><div class="image '+('dark' if '-white-' in item['id'] else '')+'"><img loading="lazy" src="'+html.escape(src)+'"></div><figcaption>'+html.escape(item['label'])+'<small>'+html.escape(', '.join(item['pages']))+'<br>'+html.escape(item['status'])+'</small></figcaption></figure>')
    page='<!doctype html><meta charset="utf-8"><title>本地素材拆分核对</title><style>body{font:14px "Microsoft YaHei",sans-serif;background:#f4f7f5;color:#225e59;margin:30px}main{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:16px}figure{margin:0;padding:12px;background:white;border:1px solid #dce7e1;border-radius:10px}.image{height:150px;display:grid;place-items:center;background:#f1f5f1}.dark{background:#225e59}img{max-width:100%;max-height:150px;object-fit:contain}small{display:block;color:#7b8f86;line-height:1.8;margin-top:8px}</style><h1>五张最终图 · 独立素材核对</h1><p>仅本地设计文件，不发布到参赛网站。旧第二张图不采用。PNG复用与新增分开登记；图标为原生SVG，控件由网页实现。</p><p>素材 '+str(len(manifest))+' 项；待补 '+html.escape(', '.join(missing) or '无')+'</p><main>'+''.join(cards)+'</main>'
    (DESIGN/'本地素材总览.html').write_text(page,encoding='utf-8')
    print(json.dumps({k:report[k] for k in ['total_files','raster_files','svg_files','missing_new_images']},ensure_ascii=False))


if __name__ == '__main__':main()
