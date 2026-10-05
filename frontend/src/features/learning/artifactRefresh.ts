type FormalBuffer = {text:string;baseline:string;edit:number;initialized:boolean;pending?:unknown;conflict?:boolean;thread?:{version:number}};
export function formalRefreshPolicy(buffer:FormalBuffer,nextVersion:number,editAtRead:number,initial:boolean,automatic:boolean) {
  const protectedEdit=buffer.text!==buffer.baseline||!!buffer.pending||!!buffer.conflict;
  return {
    version:automatic&&protectedEdit&&buffer.thread?buffer.thread.version:nextVersion,
    adoptText:buffer.edit===editAtRead&&((initial&&!buffer.initialized)||(automatic&&!protectedEdit)),
    clearConflict:!automatic,
  };
}
