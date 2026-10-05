export function restoreAssistantFocus(previous:HTMLElement|null,panel:HTMLElement|null,entry:HTMLElement|null) {
  const available=(element:HTMLElement|null)=>!!element&&element.isConnected&&element.tagName!=='BODY'&&element.tagName!=='HTML'&&!element.hasAttribute('disabled')&&element.getAttribute('aria-disabled')!=='true'&&!panel?.contains(element);
  if(available(previous))previous!.focus();
  else if(available(entry))entry!.focus();
}
