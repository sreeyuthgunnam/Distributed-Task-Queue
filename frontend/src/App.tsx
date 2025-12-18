import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Tasks from './pages/Tasks'
import Queues from './pages/Queues'
import Workers from './pages/Workers'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="tasks" element={<Tasks />} />
        <Route path="queues" element={<Queues />} />
        <Route path="workers" element={<Workers />} />
      </Route>
    </Routes>
  )
}

export default App
