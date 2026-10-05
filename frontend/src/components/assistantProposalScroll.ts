/** Keep the candidate's action row at its previous visible position after layout. */
export function restoreProposalAnchor(scroll:Pick<HTMLElement,'scrollTop'|'style'>,card:Pick<HTMLElement,'isConnected'|'getBoundingClientRect'>,previousBottom:number,collapsedBody?:Pick<HTMLElement,'scrollTop'>):void {
  if(!card.isConnected)return;
  if(collapsedBody)collapsedBody.scrollTop=0;
  const delta=card.getBoundingClientRect().bottom-previousBottom;
  const previousBehavior=scroll.style.scrollBehavior;
  scroll.style.scrollBehavior='auto';
  scroll.scrollTop+=delta;
  scroll.style.scrollBehavior=previousBehavior;
}
