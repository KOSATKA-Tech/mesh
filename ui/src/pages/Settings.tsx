import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import axios from 'axios';
import { Save, Mail, Globe, Shield, RefreshCw, Info } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { clsx } from 'clsx';

const Tooltip = ({ text }: { text: string }) => (
  <motion.div
    initial={{ opacity: 0, y: 5, scale: 0.98 }}
    animate={{ opacity: 1, y: 0, scale: 1 }}
    exit={{ opacity: 0, y: 3, scale: 0.98 }}
    className="absolute z-50 px-4 py-2 bg-primary text-primary-foreground text-[10px] font-black uppercase tracking-widest rounded-lg shadow-2xl pointer-events-none -top-10 left-0 whitespace-nowrap"
  >
    {text}
    <div className="absolute -bottom-1 left-4 w-2 h-2 bg-primary rotate-45" />
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
    <div className="flex h-[60vh] items-center justify-center">
       <div className="text-[13px] font-black uppercase tracking-luxury animate-pulse opacity-20 italic">Accessing Core Config...</div>
    </div>
  );

  return (
    <div className="space-y-12 max-w-5xl pb-32">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-6">
        <div className="space-y-2 text-left">
          <h1 className="text-5xl lg:text-7xl font-black tracking-tighter uppercase italic opacity-95">Settings</h1>
          <p className="text-[12px] lg:text-[14px] font-bold opacity-40 uppercase tracking-[0.4em]">Global Mesh Configuration & Security Parameters</p>
        </div>
        <button 
          onClick={handleSave}
          disabled={updateBatch.isPending}
          className="hidden sm:flex items-center space-x-4 bg-primary text-primary-foreground px-10 py-5 rounded-2xl font-black uppercase tracking-widest text-[12px] hover:opacity-90 transition-all shadow-2xl active:scale-95"
        >
          {updateBatch.isPending ? <RefreshCw className="h-5 w-5 animate-spin" /> : <Save className="h-5 w-5" />}
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
          className="glass p-10 rounded-[40px] space-y-8 relative group hover:border-border transition-colors shadow-lg"
        >
          <AnimatePresence>
            {hoveredSection === 'smtp' && <Tooltip text="Outgoing email settings." />}
          </AnimatePresence>
          
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4 opacity-40">
              <Mail className="h-5 w-5" />
              <h2 className="font-black uppercase tracking-[0.2em] text-[12px] italic">SMTP Communications</h2>
            </div>
            <Info className="h-4 w-4 opacity-10 group-hover:opacity-30 transition-opacity" />
          </div>

          <div className="space-y-6">
            <div className="space-y-2">
              <label className="text-[10px] opacity-30 uppercase font-black tracking-widest ml-1">Relay Host</label>
              <input 
                className="w-full bg-foreground/[0.03] border border-border rounded-xl px-5 py-4 text-base outline-none focus:border-primary/40 transition-all italic opacity-80" 
                value={localConfig.smtp_host || ''} 
                onChange={e => updateKey('smtp_host', e.target.value)}
                placeholder="smtp.example.com"
              />
            </div>
            <div className="grid grid-cols-3 gap-6">
              <div className="col-span-1 space-y-2">
                <label className="text-[10px] opacity-30 uppercase font-black tracking-widest ml-1">Port</label>
                <input 
                  type="number"
                  className="w-full bg-foreground/[0.03] border border-border rounded-xl px-5 py-4 text-base outline-none focus:border-primary/40 transition-all opacity-80" 
                  value={localConfig.smtp_port || 587} 
                  onChange={e => updateKey('smtp_port', parseInt(e.target.value))}
                />
              </div>
              <div className="col-span-2 space-y-2">
                <label className="text-[10px] opacity-30 uppercase font-black tracking-widest ml-1">Sender Entity</label>
                <input 
                  className="w-full bg-foreground/[0.03] border border-border rounded-xl px-5 py-4 text-base outline-none focus:border-primary/40 transition-all italic opacity-80" 
                  value={localConfig.smtp_from || ''} 
                  onChange={e => updateKey('smtp_from', e.target.value)}
                  placeholder="noreply@kosatka.tech"
                />
              </div>
            </div>
            <div className="space-y-2 text-left">
              <label className="text-[10px] opacity-30 uppercase font-black tracking-widest ml-1">Credentials</label>
              <div className="space-y-3">
                <input 
                  className="w-full bg-foreground/[0.03] border border-border rounded-xl px-5 py-4 text-base outline-none focus:border-primary/40 transition-all opacity-80" 
                  value={localConfig.smtp_user || ''} 
                  onChange={e => updateKey('smtp_user', e.target.value)}
                  placeholder="Username"
                />
                <input 
                  type="password"
                  className="w-full bg-foreground/[0.03] border border-border rounded-xl px-5 py-4 text-base outline-none focus:border-primary/40 transition-all opacity-80" 
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
          className="glass p-10 rounded-[40px] relative group hover:border-border transition-colors shadow-lg flex flex-col"
        >
          <AnimatePresence>
            {hoveredSection === 'dns' && <Tooltip text="Automates node domain records." />}
          </AnimatePresence>

          <div className="flex items-center justify-between mb-8">
            <div className="flex items-center space-x-4 opacity-40">
              <Globe className="h-5 w-5" />
              <h2 className="font-black uppercase tracking-[0.2em] text-[12px] italic">DNS Orchestration</h2>
            </div>
            <Info className="h-4 w-4 opacity-10 group-hover:opacity-30 transition-opacity" />
          </div>

          <div className="space-y-6">
             <div className="space-y-2">
              <label className="text-[10px] opacity-30 uppercase font-black tracking-widest ml-1">Root Domain</label>
              <input 
                className="w-full bg-foreground/[0.03] border border-border rounded-xl px-5 py-4 text-base outline-none focus:border-primary/40 transition-all italic opacity-80" 
                value={localConfig.base_domain || ''} 
                onChange={e => updateKey('base_domain', e.target.value)}
                placeholder="nodes.kosatka.tech"
              />
            </div>
            <div className="space-y-2">
              <label className="text-[10px] opacity-30 uppercase font-black tracking-widest ml-1">Provider API</label>
              <select 
                className="w-full bg-foreground/[0.03] border border-border rounded-xl px-5 py-4 text-base outline-none focus:border-primary/40 appearance-none cursor-pointer uppercase font-black tracking-widest opacity-80"
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
            
            {['cloudflare', 'digitalocean', 'hetzner', 'beget'].includes(localConfig.dns_provider) && (
              <motion.div 
                initial={{ opacity: 0, height: 0 }} 
                animate={{ opacity: 1, height: 'auto' }} 
                className="space-y-2 pt-4 border-t border-border overflow-hidden"
              >
                <label className="text-[10px] opacity-30 uppercase font-black tracking-widest ml-1">Authentication Token</label>
                <input 
                  type="password" 
                  className="w-full bg-foreground/[0.05] border border-border rounded-xl px-5 py-4 text-base outline-none focus:border-primary/50 transition-all opacity-80" 
                  value={localConfig[`${localConfig.dns_provider === 'beget' ? 'beget_api_key' : localConfig.dns_provider + '_token'}`] || ''} 
                  onChange={e => updateKey(localConfig.dns_provider === 'beget' ? 'beget_api_key' : localConfig.dns_provider + '_token', e.target.value)} 
                />
              </motion.div>
            )}
          </div>
        </motion.div>

        {/* Global Security */}
        <motion.div 
          onMouseEnter={() => setHoveredSection('security')}
          onMouseLeave={() => setHoveredSection(null)}
          initial={{ opacity: 0, y: 20 }} 
          animate={{ opacity: 1, y: 0 }} 
          transition={{ delay: 0.2 }} 
          className="glass p-10 rounded-[40px] space-y-10 lg:col-span-2 relative group hover:border-border transition-colors shadow-xl"
        >
          <AnimatePresence>
            {hoveredSection === 'security' && <Tooltip text="Global limits and protection." />}
          </AnimatePresence>

          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4 opacity-40">
              <Shield className="h-5 w-5" />
              <h2 className="font-black uppercase tracking-[0.2em] text-[12px] italic">Hardening & Integrity</h2>
            </div>
            <Info className="h-4 w-4 opacity-10 group-hover:opacity-30 transition-opacity" />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-10">
            <div className="bg-foreground/[0.02] border border-border p-8 rounded-[35px] space-y-4">
              <label className="text-[10px] opacity-30 uppercase font-black tracking-widest block text-left">API Rate Limit</label>
              <div className="flex items-end space-x-3">
                <input 
                  type="number"
                  className="bg-transparent border-b-2 border-border text-3xl outline-none w-24 font-black focus:border-primary/40 transition-all text-foreground" 
                  value={localConfig.global_rate_limit || 60} 
                  onChange={e => updateKey('global_rate_limit', parseInt(e.target.value))}
                />
                <span className="text-[11px] opacity-20 font-black uppercase mb-1">req/min</span>
              </div>
            </div>

            <div className="bg-foreground/[0.02] border border-border p-8 rounded-[35px] space-y-4 flex flex-col justify-center">
              <div className="flex items-center space-x-5">
                <div className="relative inline-flex h-8 w-14 items-center rounded-full bg-foreground/[0.05] border border-border cursor-pointer transition-colors" onClick={() => updateKey('ddos_protection_enabled', !localConfig.ddos_protection_enabled)}>
                  <span className={clsx("inline-block h-6 w-6 transform rounded-full bg-primary transition-transform duration-500 shadow-lg", localConfig.ddos_protection_enabled ? "translate-x-7" : "translate-x-1")} />
                </div>
                <span className="text-[11px] opacity-40 uppercase font-black tracking-widest text-left">DDoS Mitigation</span>
              </div>
            </div>

            <div className="bg-foreground/[0.02] border border-border p-8 rounded-[35px] space-y-4 text-left">
              <label className="text-[10px] opacity-30 uppercase font-black tracking-widest block">Bot Username</label>
              <input 
                className="w-full bg-transparent border-b-2 border-border text-xl outline-none focus:border-primary/40 transition-all italic opacity-90 font-bold text-foreground" 
                value={localConfig.bot_username || ''} 
                onChange={e => updateKey('bot_username', e.target.value)}
                placeholder="KosatkaVPNBot"
              />
            </div>
          </div>
        </motion.div>
      </div>

      <div className="sm:hidden fixed bottom-12 right-10 z-50">
        <button 
          onClick={handleSave}
          disabled={updateBatch.isPending}
          className="flex items-center justify-center bg-primary text-primary-foreground h-20 w-20 rounded-[30px] shadow-2xl active:scale-90 transition-all"
        >
          {updateBatch.isPending ? <RefreshCw className="h-8 w-8 animate-spin" /> : <Save className="h-8 w-8" />}
        </button>
      </div>
    </div>
  );
}
