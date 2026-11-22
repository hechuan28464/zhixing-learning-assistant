"""Invoke the fixed OpenMAIC domain contract. Never executes learner source."""
import json,shutil,subprocess
from pathlib import Path
from ..service import Conflict
ROOT=Path(__file__).resolve().parents[2]
PROJECT=json.loads((Path(__file__).parent/'project.json').read_text(encoding='utf-8'))
class EngineUnavailable(RuntimeError):pass

def transition(command,state=None,payload=None):
    node=shutil.which('node')
    if not node:raise EngineUnavailable('项目流程暂时不可用，请检查部署中的Node运行环境。')
    data=json.dumps(dict(command=command,project=PROJECT,state=state,payload=payload),ensure_ascii=False)
    try:result=subprocess.run([node,str(ROOT/'integrations/openmaic/bridge.mjs')],input=data,capture_output=True,text=True,encoding='utf-8',timeout=10,cwd=ROOT)
    except (OSError,subprocess.TimeoutExpired):raise EngineUnavailable('项目流程引擎暂时不可用，保存的记录仍然保留。') from None
    try:parsed=json.loads(result.stdout)
    except ValueError:raise EngineUnavailable('项目流程引擎暂时不可用，请检查构建。') from None
    if not parsed.get('ok'):raise Conflict('当前阶段条件尚未满足，不能跳过保存、确认或测试。')
    return parsed
