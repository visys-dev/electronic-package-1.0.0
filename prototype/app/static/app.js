'use strict';
const $ = id => document.getElementById(id);
const eventNames={created:'Заявку створено',assigned:'Призначено виконавця',state_changed:'Змінено стан',comment_added:'Додано повідомлення'};
const kindNames={comment:'Коментар',solution:'Рішення'};
const roleNames={requester:'Заявник',specialist:'Спеціаліст',coordinator:'Координатор',administrator:'Адміністратор'};
const states={new:'Нова',assigned:'Призначена',in_progress:'У роботі',resolved:'Вирішена',closed:'Закрита'};
let session=null, ticket=null, createAttempt=null;
let cursors={tickets:null,comments:null,history:null};
function message(text){$('status').textContent=text;}
function clearFieldErrors(){
 document.querySelectorAll('.field-error').forEach(e=>e.remove());
 document.querySelectorAll('[aria-invalid="true"]').forEach(e=>{e.removeAttribute('aria-invalid');e.removeAttribute('aria-describedby');});
}
function showFieldErrors(errors){
 let first=null;
 for(const error of errors){
  for(const control of document.querySelectorAll(`[name="${CSS.escape(error.field)}"]`)){
   if(control.closest('[hidden]'))continue;
   const explanation=document.createElement('span');
   explanation.id='error-'+control.form.id+'-'+control.name;explanation.className='field-error';explanation.textContent=error.message;
   control.setAttribute('aria-invalid','true');control.setAttribute('aria-describedby',explanation.id);control.after(explanation);first=first||control;
  }
 }
 if(first)first.focus();
}
function clearSession(){session=null;ticket=null;createAttempt=null;$('workspace').hidden=true;$('card').hidden=true;$('login-panel').hidden=false;$('logout').hidden=true;$('identity').textContent='';document.querySelectorAll('form').forEach(f=>f.reset());['tickets','comments','history'].forEach(id=>$(id).replaceChildren());}
async function api(path,method='GET',body=null,headers={}){
 const options={method,headers:{...headers},credentials:'same-origin'};
 if(method!=='GET'&&session)options.headers['X-CSRF-Token']=session.csrfToken;
 if(body!==null){options.headers['Content-Type']='application/json';options.body=JSON.stringify(body);}
 const response=await fetch('/api/v1'+path,options);
 const data=response.status===204?null:await response.json();
 if(!response.ok){
  if(response.status===401)clearSession();
  if(data.code==='CSRF_FAILED'&&session){session=await api('/session');}
  if(data.code==='VERSION_CONFLICT'&&ticket){await openTicket(ticket.id);}
  showFieldErrors(data.fieldErrors||[]);
  const detail=(data.fieldErrors||[]).map(e=>e.field+': '+e.message).join(' ');
  throw new Error((data.message||'Помилка запиту.')+' '+detail);
 }
 return data;
}
async function perform(button,action){
 if(button.disabled)return;clearFieldErrors();button.disabled=true;message('Виконується…');
 try{await action();message('Готово.');}catch(e){message(e.message||'З’єднання перервано. Результат невідомий; повторіть дію.');}
 finally{button.disabled=false;}
}
function formAction(id,action){$(id).addEventListener('submit',event=>{event.preventDefault();const form=event.currentTarget;perform(form.querySelector('button'),()=>action(Object.fromEntries(new FormData(form)),form));});}
function eventText(item){
 const change=item.changes.state;
 return change?`${eventNames[item.eventType]||'Подія'}: ${change.old?(states[change.old]||change.old)+' → ':''}${states[change.new]||change.new}`:(eventNames[item.eventType]||'Подія');
}
function listItem(id,text){const li=document.createElement('li');li.textContent=text;$(id).append(li);}
async function loadTickets(append=false){
 const page=await api('/tickets'+(append&&cursors.tickets?'?cursor='+encodeURIComponent(cursors.tickets):''));
 if(!append)$('tickets').replaceChildren();
 for(const t of page.items){const li=document.createElement('li'),button=document.createElement('button');button.textContent=`№${t.number} · ${t.title} · ${states[t.state]||t.state}`;button.onclick=()=>perform(button,()=>openTicket(t.id));li.append(button);$('tickets').append(li);}
 if(!append&&!page.items.length)listItem('tickets','Заявок поки немає.');
 cursors.tickets=page.nextCursor;$('more-tickets').hidden=!page.nextCursor;
}
async function loadEvents(kind,append=false){
 const id=ticket.id,page=await api(`/tickets/${id}/${kind}`+(append&&cursors[kind]?'?cursor='+encodeURIComponent(cursors[kind]):''));
 if(!append)$(kind).replaceChildren();
 for(const item of page.items){listItem(kind,kind==='comments'?`${new Date(item.createdAt).toLocaleString('uk-UA')} · ${kindNames[item.kind]||'Повідомлення'}\n${item.body}`:`${new Date(item.occurredAt).toLocaleString('uk-UA')} · ${eventText(item)}`);}
 cursors[kind]=page.nextCursor;$('more-'+kind).hidden=!page.nextCursor;
}
async function openTicket(id){
 ticket=await api('/tickets/'+id);$('card').hidden=false;
 $('ticket-heading').textContent=`Заявка №${ticket.number}: ${ticket.title}`;
 $('ticket-details').textContent=states[ticket.state]||ticket.state;
 $('ticket-description').textContent=ticket.description;
 const specialist=ticket.assigneeId===session.userId&&session.roles.includes('specialist');
 $('start').hidden=!(specialist&&ticket.state==='assigned');$('solution').hidden=!(specialist&&ticket.state==='in_progress');
 $('confirm').hidden=!(ticket.requesterId===session.userId&&ticket.state==='resolved');$('comment').hidden=ticket.state==='closed';
 $('assignment').hidden=true;
 if(session.roles.includes('coordinator')&&ticket.state==='new'){
  try{const result=await api(`/queues/${ticket.queueId}/assignees`),select=$('assignment').elements.assigneeId;select.replaceChildren();for(const u of result.items)select.add(new Option(u.displayName,u.id));$('assignment').hidden=false;}catch(e){message(e.message);}
 }
 await Promise.all([loadEvents('comments'),loadEvents('history')]);
}
async function workspace(){
 $('login-panel').hidden=true;$('workspace').hidden=false;$('logout').hidden=false;$('identity').textContent=session.roles.map(r=>roleNames[r]||r).join(', ');
 $('create-panel').hidden=!session.roles.includes('requester');
 if(session.roles.includes('requester')){const result=await api('/categories'),select=$('create').elements.categoryId;select.replaceChildren();for(const c of result.items)select.add(new Option(c.name,c.id));}
 await loadTickets();
}
formAction('login',async(data,form)=>{session=await api('/session','POST',data);form.reset();await workspace();});
formAction('create',async(data,form)=>{
 const payload={...data,title:data.title.trim(),description:data.description.trim()},encoded=JSON.stringify(payload);
 if(!createAttempt||createAttempt.encoded!==encoded)createAttempt={encoded,key:crypto.randomUUID()};
 const t=await api('/tickets','POST',payload,{'Idempotency-Key':createAttempt.key});createAttempt=null;form.reset();await loadTickets();await openTicket(t.id);
});
formAction('assignment',async data=>{await api(`/tickets/${ticket.id}/assignment`,'POST',{...data,expectedVersion:ticket.version});await openTicket(ticket.id);await loadTickets();});
formAction('solution',async(data,form)=>{await api(`/tickets/${ticket.id}/state`,'POST',{toState:'resolved',text:data.text,expectedVersion:ticket.version});form.reset();await openTicket(ticket.id);await loadTickets();});
formAction('comment',async(data,form)=>{await api(`/tickets/${ticket.id}/comments`,'POST',{...data,visibility:'public',expectedVersion:ticket.version});form.reset();await openTicket(ticket.id);});
$('start').onclick=()=>perform($('start'),async()=>{await api(`/tickets/${ticket.id}/state`,'POST',{toState:'in_progress',expectedVersion:ticket.version});await openTicket(ticket.id);await loadTickets();});
$('confirm').onclick=()=>perform($('confirm'),async()=>{await api(`/tickets/${ticket.id}/state`,'POST',{toState:'closed',expectedVersion:ticket.version,solutionCommentId:ticket.solutionCommentId});await openTicket(ticket.id);await loadTickets();});
$('logout').onclick=()=>perform($('logout'),async()=>{await api('/session','DELETE');clearSession();});
$('refresh').onclick=()=>perform($('refresh'),()=>loadTickets());
$('more-tickets').onclick=()=>perform($('more-tickets'),()=>loadTickets(true));
for(const kind of ['comments','history'])$('more-'+kind).onclick=()=>perform($('more-'+kind),()=>loadEvents(kind,true));
(async()=>{try{session=await api('/session');await workspace();}catch(e){clearSession();message('Увійдіть навчальним обліковим записом.');}})();
