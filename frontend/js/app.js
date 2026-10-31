const $=id=>document.getElementById(id);
const api='/api/v1/files';let files=[];
const safe=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function notify(message,error=false){$('message').textContent=message;$('message').className='message'+(error?' error':'')}
async function refresh(){
 try{
  const health=await fetch('/health');if(!health.ok)throw Error('API unavailable');
  const result=await fetch(api);if(!result.ok)throw Error('Cannot list files');
  files=await result.json();$('dot').classList.add('ok');$('connection').textContent='API connected';
  $('total').textContent=files.length;
  $('processed').textContent=files.filter(f=>f.status==='completed').length;
  $('records').textContent=files.reduce((sum,f)=>sum+(f.rows_count||0),0).toLocaleString();
  $('rows').innerHTML=files.length?files.map(f=>`<tr><td>${safe(f.filename)}</td><td>${safe(f.kind)}</td><td>${f.rows_count??'—'}</td><td>${safe(f.status)}</td><td><div class="actions"><button class="btn secondary small" data-preview="${safe(f.id)}">Preview</button><button class="btn secondary small" data-download="${safe(f.id)}" data-format="json">JSON ↓</button>${f.kind==='pdf'?'':`<button class="btn secondary small" data-download="${safe(f.id)}" data-format="csv">CSV ↓</button>`}</div></td></tr>`).join(''):'<tr><td colspan="5">No uploads yet.</td></tr>';
 }catch(e){$('connection').textContent='API offline';$('dot').classList.remove('ok');notify(e.message,true);$('rows').innerHTML='<tr><td colspan="5">Start FastAPI to load your workspace.</td></tr>'}
}
async function preview(id){
 try{const response=await fetch(`${api}/${encodeURIComponent(id)}/data?limit=20`);if(!response.ok)throw Error('Preview unavailable');$('previewtitle').textContent=files.find(f=>f.id===id)?.filename||id;$('preview').textContent=JSON.stringify(await response.json(),null,2)}
 catch(e){$('preview').textContent=e.message}
}
async function upload(file){
 if(!file)return;
 if(file.size>10*1024*1024){notify('Maximum file size is 10 MB',true);return}
 $('chosen').hidden=false;$('chosen').textContent='Selected: '+file.name;
 $('browse').disabled=true;notify('Processing file…');
 const form=new FormData();form.append('file',file);
 try{const response=await fetch(api+'/upload',{method:'POST',body:form});const data=await response.json();if(!response.ok)throw Error(data.detail||'Upload failed');notify('Processed '+file.name);await refresh();await preview(data.id)}
 catch(e){notify(e.message,true)}
 finally{$('browse').disabled=false;$('file').value=''}
}
$('browse').onclick=()=>$('file').click();
$('file').onchange=e=>upload(e.target.files[0]);
$('refresh').onclick=refresh;
$('rows').onclick=e=>{const b=e.target.closest('button');if(!b)return;if(b.dataset.preview)preview(b.dataset.preview);if(b.dataset.download)location.href=`${api}/${encodeURIComponent(b.dataset.download)}/download?format=${b.dataset.format}`};
const drop=$('drop');
drop.ondragover=e=>{e.preventDefault();drop.classList.add('drag')};
drop.ondragleave=()=>drop.classList.remove('drag');
drop.ondrop=e=>{e.preventDefault();drop.classList.remove('drag');upload(e.dataTransfer.files[0])};
refresh();
