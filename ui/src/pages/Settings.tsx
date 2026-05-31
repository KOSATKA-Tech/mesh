import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import axios from 'axios';
import { Save, Mail, Globe, Shield, RefreshCw, Info } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { clsx } from 'clsx';

const Tooltip = ({ text }: { text: string }) => (
  <motion.div
    initial={{ opacity: 0, y: 10, scale: 0.95 }}
    animate={{ opacity: 1, y: 0, scale: 1 }}
    exit={{ opacity: 0, y: 5, scale: 0.95 }}
    className="absolute z-50 px-4 py-2 bg-white text-black text-[10px] font-black uppercase tracking-widest rounded-lg shadow-2xl pointer-events-none -top-12 left-0 whitespace-nowrap"
  >
    {text}
    <div className="absolute -bottom-1 left-4 w-2 h-2 bg-white rotate-45" />
  </motion.div>
);

export default function Settings() {
  const [localConfig, setLocalConfig] = useState<any>({});
  const [hoveredSection, setHoveredSection] = useState<string | null>(null);
  
  const { isLoading } = useQuery({
    queryKey: ['system-configs'],
    queryFn: async () => {
      const resp = await axios.get('/api/v1/config/');
      const obj: any = {};
      resp.data.forEach((c: any) => {
        try {
          obj[c.key] = JSON.parse(c.value);
        } catch {
          obj[c.key] = c.value;
        }
      });
      setLocalConfig((prev: any) => {
        if (Object.keys(prev).length === 0) return obj;
        return prev;
      });
      return obj;
    }
  });

  const updateBatch = useMutation({
    mutationFn: async (data: any) => {
      await axios.post('/api/v1/config/batch', data);
    },
  });

  const handleSave = () => {
    updateBatch.mutate(localConfig);
  };

  const updateKey = (key: string, val: any) => {
    setLocalConfig({ ...localConfig, [key]: val });
  };

  if (isLoading && Object.keys(localConfig).length === 0) return (
    <div className="flex h-[50vh] items-center justify-center">
       <div className="text-[11px] font-black uppercase tracking-luxury animate-pulse text-white/20 italic">Accessing Core Config...</div>
    </div>
  );

  return (
    <div className="space-y-12 max-w-5xl pb-24 lg:pb-0">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div className="space-y-1">
          <h1 className="text-4xl lg:text-5xl font-black tracking-luxury uppercase italic text-white/90">Settings</h1>
          <p className="text-[11px] font-bold text-white/20 uppercase tracking-widest">Global Mesh Configuration & Security Parameters</p>
        </div>
        <button 
          onClick={handleSave}
          disabled={updateBatch.isPending}
          className="hidden sm:flex items-center space-x-3 bg-white text-black px-8 py-4 rounded-2xl font-black uppercase tracking-widest text-[11px] hover:bg-white/90 transition-all shadow-[0_0_30px_rgba(255,255,255,0.1)] active:scale-95"
        >
          {updateBatch.isPending ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
          <span>{updateBatch.isPending ? 'Syncing...' : 'Apply Changes'}</span>
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* SMTP Section */}
        <motion.div 
          onMouseEnter={() => setHoveredSection('smtp')}
          onMouseLeave={() => setHoveredSection(null)}
          initial={{ opacity: 0, y: 20 }} 
          animate={{ opacity: 1, y: 0 }} 
          className="glass p-10 rounded-[40px] space-y-8 relative group hover:border-white/20 transition-colors"
        >
          <AnimatePresence>
            {hoveredSection === 'smtp' && <Tooltip text="Configures outgoing email for trial access and system alerts." />}
          </AnimatePresence>
          
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3 text-white/40">
              <Mail className="h-4 w-4" />
              <h2 className="font-black uppercase tracking-[0.2em] text-[11px] italic">SMTP Communications</h2>
            </div>
            <Info className="h-3.5 w-3.5 text-white/10 group-hover:text-white/30 transition-colors" />
          </div>

          <div className="space-y-6">
            <div className="space-y-2">
              <label className="text-[10px] text-white/20 uppercase font-black tracking-widest ml-1">Relay Host</label>
              <input 
                className="w-full bg-white/[0.02] border border-white/5 rounded-2xl px-5 py-4 text-sm outline-none focus:border-white/20 focus:bg-white/[0.04] transition-all italic text-white/80" 
                value={localConfig.smtp_host || ''} 
                onChange={e => updateKey('smtp_host', e.target.value)}
                placeholder="smtp.mission-control.io"
              />
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div className="col-span-1 space-y-2">
                <label className="text-[10px] text-white/20 uppercase font-black tracking-widest ml-1">Port</label>
                <input 
                  type="number"
                  className="w-full bg-white/[0.02] border border-white/5 rounded-2xl px-5 py-4 text-sm outline-none focus:border-white/20 transition-all text-white/80" 
                  value={localConfig.smtp_port || 587} 
                  onChange={e => updateKey('smtp_port', parseInt(e.target.value))}
                />
              </div>
              <div className="col-span-2 space-y-2">
                <label className="text-[10px] text-white/20 uppercase font-black tracking-widest ml-1">Sender Entity</label>
                <input 
                  className="w-full bg-white/[0.02] border border-white/5 rounded-2xl px-5 py-4 text-sm outline-none focus:border-white/20 transition-all italic text-white/80" 
                  value={localConfig.smtp_from || ''} 
                  onChange={e => updateKey('smtp_from', e.target.value)}
                  placeholder="noreply@kosatka.tech"
                />
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-[10px] text-white/20 uppercase font-black tracking-widest ml-1">Credentials</label>
              <div className="space-y-3">
                <input 
                  className="w-full bg-white/[0.02] border border-white/5 rounded-2xl px-5 py-4 text-sm outline-none focus:border-white/20 transition-all text-white/80" 
                  value={localConfig.smtp_user || ''} 
                  onChange={e => updateKey('smtp_user', e.target.value)}
                  placeholder="Username"
                />
                <input 
                  type="password"
                  className="w-full bg-white/[0.02] border border-white/5 rounded-2xl px-5 py-4 text-sm outline-none focus:border-white/20 transition-all text-white/80" 
                  value={localConfig.smtp_password || ''} 
                  onChange={e => updateKey('smtp_password', e.target.value)}
                  placeholder="••••••••"
                />
              </div>
            </div>
          </div>
        </motion.div>

        {/* DNS Automation Section */}
        <motion.div 
          onMouseEnter={() => setHoveredSection('dns')}
          onMouseLeave={() => setHoveredSection(null)}
          initial={{ opacity: 0, y: 20 }} 
          animate={{ opacity: 1, y: 0 }} 
          transition={{ delay: 0.1 }} 
          className="glass p-10 rounded-[40px] space-y-8 relative group hover:border-white/20 transition-colors"
        >
          <AnimatePresence>
            {hoveredSection === 'dns' && <Tooltip text="Automates domain record creation for new nodes via API." />}
          </AnimatePresence>

          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3 text-white/40">
              <Globe className="h-4 w-4" />
              <h2 className="font-black uppercase tracking-[0.2em] text-[11px] italic">DNS Orchestration</h2>
            </div>
            <Info className="h-3.5 w-3.5 text-white/10 group-hover:text-white/30 transition-colors" />
          </div>

          <div className="space-y-6">
             <div className="space-y-2">
              <label className="text-[10px] text-white/20 uppercase font-black tracking-widest ml-1">Root Domain</label>
              <input 
                className="w-full bg-white/[0.02] border border-white/5 rounded-2xl px-5 py-4 text-sm outline-none focus:border-white/20 transition-all italic text-white/80" 
                value={localConfig.base_domain || ''} 
                onChange={e => updateKey('base_domain', e.target.value)}
                placeholder="nodes.kosatka.tech"
              />
            </div>
            <div className="space-y-2">
              <label className="text-[10px] text-white/20 uppercase font-black tracking-widest ml-1">Provider API</label>
              <select 
                className="w-full bg-white/[0.02] border border-white/5 rounded-2xl px-5 py-4 text-sm outline-none focus:border-white/20 appearance-none cursor-pointer uppercase font-bold tracking-widest text-white/80"
                value={localConfig.dns_provider || 'manual'}
                onChange={e => updateKey('dns_provider', e.target.value)}
              >
                <option value="manual">Manual Entry</option>
                <option value="cloudflare">Cloudflare</option>
                <option value="digitalocean">DigitalOcean</option>
                <option value="hetzner">Hetzner</option>
                <option value="beget">Beget API</option>
              </select>
            </div>
            
            <AnimatePresence mode="wait">
              {['cloudflare', 'digitalocean', 'hetzner', 'beget'].includes(localConfig.dns_provider) && (
                <motion.div 
                  key={localConfig.dns_provider}
                  initial={{ opacity: 0, x: -10 }} 
                  animate={{ opacity: 1, x: 0 }} 
                  exit={{ opacity: 0, x: 10 }}
                  className="space-y-4 pt-2 border-t border-white/5"
                >
                  <div className="space-y-2">
                    <label className="text-[9px] text-white/20 uppercase font-black tracking-widest ml-1">Authentication Token</label>
                    <input 
                      type="password" 
                      className="w-full bg-white/[0.04] border border-white/10 rounded-xl px-5 py-3 text-sm outline-none focus:border-white/30 transition-all text-white/80" 
                      value={localConfig[`${localConfig.dns_provider === 'beget' ? 'beget_api_key' : localConfig.dns_provider + '_token'}`] || ''} 
                      onChange={e => updateKey(localConfig.dns_provider === 'beget' ? 'beget_api_key' : localConfig.dns_provider + '_token', e.target.value)} 
                    />
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </motion.div>

        {/* Global Security */}
        <motion.div 
          onMouseEnter={() => setHoveredSection('security')}
          onMouseLeave={() => setHoveredSection(null)}
          initial={{ opacity: 0, y: 20 }} 
          animate={{ opacity: 1, y: 0 }} 
          transition={{ delay: 0.2 }} 
          className="glass p-10 rounded-[40px] space-y-8 lg:col-span-2 relative group hover:border-white/20 transition-colors"
        >
          <AnimatePresence>
            {hoveredSection === 'security' && <Tooltip text="Controls global API rate limits, DDoS protection and bot settings." />}
          </AnimatePresence>

          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3 text-white/40">
              <Shield className="h-4 w-4" />
              <h2 className="font-black uppercase tracking-[0.2em] text-[11px] italic">Hardening & Integrity</h2>
            </div>
            <Info className="h-3.5 w-3.5 text-white/10 group-hover:text-white/30 transition-colors" />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="bg-white/[0.01] border border-white/5 p-6 rounded-3xl space-y-4">
              <label className="text-[10px] text-white/20 uppercase font-black tracking-widest block">API Rate Limit</label>
              <div className="flex items-end space-x-2">
                <input 
                  type="number"
                  className="bg-transparent border-b border-white/10 text-2xl outline-none w-20 font-bold focus:border-white/40 transition-all text-white" 
                  value={localConfig.global_rate_limit || 60} 
                  onChange={e => updateKey('global_rate_limit', parseInt(e.target.value))}
                />
                <span className="text-[10px] text-white/20 font-bold uppercase mb-1">req/min</span>
              </div>
            </div>

            <div className="bg-white/[0.01] border border-white/5 p-6 rounded-3xl space-y-4 flex flex-col justify-center">
              <div className="flex items-center space-x-4">
                <div className="relative inline-flex h-7 w-12 items-center rounded-full bg-white/5 border border-white/10 cursor-pointer transition-colors" onClick={() => updateKey('ddos_protection_enabled', !localConfig.ddos_protection_enabled)}>
                  <span className={clsx("inline-block h-5 w-5 transform rounded-full bg-white transition-transform duration-500 shadow-[0_0_10px_rgba(255,255,255,0.5)]", localConfig.ddos_protection_enabled ? "translate-x-6" : "translate-x-1")} />
                </div>
                <span className="text-[10px] text-white/40 uppercase font-black tracking-widest">DDoS Mitigation</span>
              </div>
            </div>

            <div className="bg-white/[0.01] border border-white/5 p-6 rounded-3xl space-y-4">
              <label className="text-[10px] text-white/20 uppercase font-black tracking-widest block">Bot Username</label>
              <input 
                className="w-full bg-transparent border-b border-white/10 text-base outline-none focus:border-white/40 transition-all italic text-white/90" 
                value={localConfig.bot_username || ''} 
                onChange={e => updateKey('bot_username', e.target.value)}
                placeholder="KosatkaVPNBot"
              />
            </div>
          </div>
        </motion.div>
      </div>

      {/* Mobile FAB */}
      <div className="sm:hidden fixed bottom-10 right-8 z-50">
        <button 
          onClick={handleSave}
          disabled={updateBatch.isPending}
          className="flex items-center justify-center bg-white text-black h-16 w-16 rounded-[24px] shadow-[0_0_50px_rgba(255,255,255,0.2)] active:scale-90 transition-all border-2 border-black"
        >
          {updateBatch.isPending ? <RefreshCw className="h-6 w-6 animate-spin" /> : <Save className="h-6 w-6" />}
        </button>
      </div>
    </div>
  );
}
