"""Export actual visible Codex records, never reconstruct dialogue from memory.

The private manifest names source JSONL files and output labels. System,
developer, reasoning and machine context records are outside visible dialogue.
Run once more after this active chat finishes to include its closing message.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

def export(source, destination):
    blob=source.read_bytes()
    selected=[];parts=[];omitted=0
    for number,line in enumerate(blob.decode().splitlines(),1):
        try:record=json.loads(line)
        except json.JSONDecodeError:continue
        if record.get('type')!='response_item':continue
        item=record.get('payload',{});kind=item.get('type')
        if kind=='message':
            role=item.get('role')
            if role not in ('user','assistant'):continue
            if role=='assistant' and item.get('phase') not in ('commentary','final','final_answer'):continue
            blocks=item.get('content',[]);texts=[]
            for block in blocks:
                if block.get('type') in ('input_text','output_text','text'):
                    text=block.get('text','')
                    if text.startswith('<environment_context>') or text.startswith('<external_codex_apps_open_page>'):
                        omitted+=1;continue
                    if '## Referenced ChatGPT conversation:' in text:
                        # The cached preview is not a full export of that ChatGPT chat.
                        marker='## My request:'
                        if marker not in text:omitted+=1;continue
                        text=text.split(marker,1)[1]
                    texts.append(text)
            if not texts:continue
            value={'type':'message','role':role,'phase':item.get('phase'),'text':'\n'.join(texts)}
            label=role.upper()
            text=value['text']
        elif kind in ('function_call','custom_tool_call'):
            value={k:item[k] for k in ('type','call_id','name','arguments','input') if k in item}
            label='TOOL CALL '+str(item.get('name',''))
            text=item.get('arguments',item.get('input',''))
        elif kind in ('function_call_output','custom_tool_call_output'):
            value={k:item[k] for k in ('type','call_id','output') if k in item}
            label='TOOL RESULT'
            text=item.get('output','')
        else:continue
        if not isinstance(text,str):text=json.dumps(text,ensure_ascii=False)
        selected.append({'timestamp':record.get('timestamp'),'native_line':number,'visible_record':value})
        parts.append('\n\n'+str(record.get('timestamp'))+' | '+label+'\n'+'='*60+'\n'+text)
    destination.parent.mkdir(parents=True,exist_ok=True)
    txt=destination.with_suffix('.txt');native=destination.with_suffix('.jsonl')
    txt.write_text('ACTUAL VISIBLE CONVERSATION EXPORT\nVerbatim recorded messages and tool trace; not a decision log.\nMachine context/hidden internal records are excluded. Attachments remain references.\n'+''.join(parts)+'\n')
    native.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in selected))
    return {'label':destination.name,'source_filename':source.name,'source_sha256':hashlib.sha256(blob).hexdigest(),
            'source_bytes_at_export':len(blob),'visible_records_exported':len(selected),'machine_context_blocks_omitted':omitted,
            'first_exported_timestamp':selected[0]['timestamp'] if selected else None,
            'last_exported_timestamp':selected[-1]['timestamp'] if selected else None,
            'text_file':txt.name,'text_sha256':hashlib.sha256(txt.read_bytes()).hexdigest(),
            'structured_file':native.name,'structured_sha256':hashlib.sha256(native.read_bytes()).hexdigest()}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True)
    a=p.parse_args();items=json.loads(a.manifest.read_text())
    records=[export(Path(r['source']),a.output_dir/r['label']) for r in items]
    summary={'exported_at_utc':datetime.now(timezone.utc).isoformat(),'mode':'native-visible-records; no memory reconstruction',
             'records':records,'active_conversation_note':'Current chat is exported through recorded cutoff; rerun after its closing message',
             'all_used_AI_conversations_complete':False,'missing_external_exports':['ChatGPT: Курування аналізу часових рядів (6aca7217-40c4-83ed-a98d-d28cd2411a70)','Gemini/Antigravity: source discovery, data collection and documentation corrections for kse-air-alert-forecasting; owner must identify/export all used chats'],
             'attachments_note':'The full text is preserved; image/file references are not a textual substitute for original attachments.'}
    a.output_dir.mkdir(parents=True,exist_ok=True)
    (a.output_dir/'export-manifest.json').write_text(json.dumps(summary,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'actual_conversations_exported':len(records),'visible_records':sum(r['visible_records_exported'] for r in records),'all_AI_export_requirement_complete':False}))
