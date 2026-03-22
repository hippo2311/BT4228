import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Portfolio from './pages/Portfolio';
import Monitoring from './pages/Monitoring';
import AIInsights from './pages/AIInsights';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="portfolio" element={<Portfolio />} />
          <Route path="monitoring" element={<Monitoring />} />
          <Route path="ai-insights" element={<AIInsights />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
