import { useState } from 'react';
import { createRoot } from 'react-dom/client';
import { PlanningPage } from '../src/features/planning/PlanningPage';
import '../src/style.css';

function Harness() {
  const [actor, setActor] = useState('actor-a');
  const [project, setProject] = useState('project-a');
  return <>
    <button onClick={() => {
      const next = project === 'project-a' ? 'project-b' : 'project-a';
      setActor(next === 'project-a' ? 'actor-a' : 'actor-b');
      setProject(next);
    }}>切换测试作用域</button>
    <PlanningPage actorKey={actor} project={project} fake={true} onPublished={async () => {}} />
  </>;
}

createRoot(document.getElementById('root')!).render(<Harness />);
