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

  const isDnsProviderSelected = ['cloudflare', 'digitalocean', 'hetzner', 'beget'].includes(localConfig.dns_provider);

  if (isLoading && Object.keys(localConfig).length === 0) return (
    <div className="flex h-full items-center justify-center">
       <div className="text-[11px] font-black uppercase tracking-luxury animate-pulse opacity-20 italic">Accessing Core Config...</div>
    </div>
  );

  return (
    <div className="space-y-10 pb-32 w-full max-w-[1400px] mx-auto transition-all duration-500">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-6">
        <div className="space-y-1 text-left">
          <h1 className="text-4xl lg:text-6xl font-black tracking-tighter uppercase italic opacity-95 text-foreground transition-all">Settings</h1>
          <p className="text-[11px] lg:text-[12px] font-bold opacity-40 uppercase tracking-[0.4em]">Global Mesh Configuration & Security Parameters</p>
        </div>
        <button 
          onClick={handleSave}
          disabled={updateBatch.isPending}
          className="hidden sm:flex items-center space-x-3 bg-primary text-primary-foreground px-8 py-3.5 rounded-xl font-black uppercase tracking-widest text-[10px] hover:opacity-90 transition-all shadow-xl active:scale-95"
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
          className="glass p-8 rounded-[32px] space-y-6 relative group hover:border-border transition-colors shadow-lg"
        >
          <AnimatePresence>
            {hoveredSection === 'smtp' && <Tooltip text="Outgoing email settings." />}
          </AnimatePresence>
          
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3 opacity-40">
              <Mail className="h-4 w-4" />
              <h2 className="font-black uppercase tracking-[0.2em] text-[11px] italic">SMTP Communications</h2>
            </div>
            <Info className="h-3.5 w-3.5 text-white/10 group-hover:text-white/30 transition-opacity" />
          </div>

          <div className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-[9px] opacity-30 uppercase font-black tracking-widest ml-1 text-left block">Relay Host</label>
              <input 
                className="w-full bg-foreground/[0.02] border border-border rounded-lg px-4 py-3 text-sm outline-none focus:border-primary/40 transition-all italic opacity-80 text-foreground" 
                value={localConfig.smtp_host || ''} 
                onChange={e => updateKey('smtp_host', e.target.value)}
                placeholder="smtp.example.com"
              />
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div className="col-span-1 space-y-1.5">
                <label className="text-[9px] opacity-30 uppercase font-black tracking-widest ml-1 text-left block">Port</label>
                <input 
                  type="number"
                  className="w-full bg-foreground/[0.02] border border-border rounded-lg px-4 py-3 text-sm outline-none focus:border-primary/40 transition-all opacity-80 text-foreground" 
                  value={localConfig.smtp_port || 587} 
                  onChange={e => updateKey('smtp_port', parseInt(e.target.value))}
                />
              </div>
              <div className="col-span-2 space-y-1.5">
                <label className="text-[9px] opacity-30 uppercase font-black tracking-widest ml-1 text-left block">Sender Entity</label>
                <input 
                  className="w-full bg-foreground/[0.02] border border-border rounded-lg px-4 py-3 text-sm outline-none focus:border-primary/40 transition-all italic opacity-80 text-foreground" 
                  value={localConfig.smtp_from || ''} 
                  onChange={e => updateKey('smtp_from', e.target.value)}
                  placeholder="noreply@kosatka.tech"
                />
              </div>
            </div>
            <div className="space-y-1.5 text-left">
              <label className="text-[9px] opacity-30 uppercase font-black tracking-widest ml-1 block">Credentials</label>
              <div className="space-y-2">
                <input 
                  className="w-full bg-foreground/[0.02] border border-border rounded-lg px-4 py-3 text-sm outline-none focus:border-primary/40 transition-all opacity-80 text-foreground" 
                  value={localConfig.smtp_user || ''} 
                  onChange={e => updateKey('smtp_user', e.target.value)}
                  placeholder="Username"
                />
                <input 
                  type="password"
                  className="w-full bg-foreground/[0.02] border border-border rounded-lg px-4 py-3 text-sm outline-none focus:border-primary/40 transition-all opacity-80 text-foreground" 
                  value={localConfig.smtp_password || ''} 
                  onChange={e => updateKey('smtp_password', e.target.value)}
                  placeholder="••••••••"
                />
              </div>
            </div>
          </div>
        </motion.div>

        {/* DNS Automation Section - TRULY DYNAMIC */}
        <motion.div 
          onMouseEnter={() => setHoveredSection('dns')}
          onMouseLeave={() => setHoveredSection(null)}
          initial={{ opacity: 0, y: 20 }} 
          animate={{ opacity: 1, y: 0 }} 
          transition={{ delay: 0.1 }} 
          className={clsx(
            "glass p-8 rounded-[32px] relative group hover:border-border transition-all duration-700 shadow-xl self-start",
            !isDnsProviderSelected ? "pb-10" : "pb-8"
          )}
        >
          <AnimatePresence>
            {hoveredSection === 'dns' && <Tooltip text="Automates node domain records." />}
          </AnimatePresence>

          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center space-x-3 opacity-40">
              <Globe className="h-4.5 w-4.5" />
              <h2 className="font-black uppercase tracking-[0.2em] text-[11px] italic">DNS Orchestration</h2>
            </div>
            <Info className="h-3.5 w-3.5 text-white/10 group-hover:text-white/30 transition-opacity" />
          </div>

          <div className="space-y-4">
             <div className="space-y-1.5">
              <label className="text-[9px] opacity-30 uppercase font-black tracking-widest ml-1 text-left block">Root Domain</label>
              <input 
                className="w-full bg-foreground/[0.02] border border-border rounded-lg px-4 py-3 text-sm outline-none focus:border-primary/40 transition-all italic opacity-80 text-foreground" 
                value={localConfig.base_domain || ''} 
                onChange={e => updateKey('base_domain', e.target.value)}
                placeholder="nodes.kosatka.tech"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-[9px] opacity-30 uppercase font-black tracking-widest ml-1 text-left block">Provider API</label>
              <select 
                className="w-full bg-foreground/[0.02] border border-border rounded-lg px-4 py-3 text-sm outline-none focus:border-primary/40 appearance-none cursor-pointer uppercase font-black tracking-widest opacity-80 text-foreground"
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
              {isDnsProviderSelected && (
                <motion.div 
                  key={localConfig.dns_provider}
                  initial={{ opacity: 0, height: 0 }} 
                  animate={{ opacity: 1, height: 'auto' }} 
                  exit={{ opacity: 0, height: 0 }}
                  className="space-y-1.5 pt-4 border-t border-border overflow-hidden text-left"
                >
                  <label className="text-[9px] opacity-30 uppercase font-black tracking-widest ml-1 block">Authentication Token</label>
                  <input 
                    type="password" 
                    className="w-full bg-foreground/[0.03] border border-border rounded-lg px-4 py-3 text-sm outline-none focus:border-primary/50 transition-all opacity-80 text-foreground" 
                    value={localConfig[`${localConfig.dns_provider === 'beget' ? 'beget_api_key' : localConfig.dns_provider + '_token'}`] || ''} 
                    onChange={e => updateKey(localConfig.dns_provider === 'beget' ? 'beget_api_key' : localConfig.dns_provider + '_token', e.target.value)} 
                  />
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
          className="glass p-10 rounded-[40px] space-y-8 lg:col-span-2 relative group hover:border-border transition-colors shadow-2xl"
        >
          <AnimatePresence>
            {hoveredSection === 'security' && <Tooltip text="Global limits and protection." />}
          </AnimatePresence>

          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4 opacity-40">
              <Shield className="h-5 w-5" />
              <h2 className="font-black uppercase tracking-[0.2em] text-[11px] italic">Hardening & Integrity</h2>
            </div>
            <Info className="h-4 w-4 opacity-10 group-hover:opacity-30 transition-opacity" />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="bg-foreground/[0.01] border border-border p-6 rounded-[24px] space-y-3">
              <label className="text-[9px] opacity-30 uppercase font-black tracking-widest block text-left">API Rate Limit</label>
              <div className="flex items-end space-x-2">
                <input 
                  type="number"
                  className="bg-transparent border-b-2 border-border text-2xl outline-none w-20 font-black focus:border-primary/40 transition-all text-foreground" 
                  value={localConfig.global_rate_limit || 60} 
                  onChange={e => updateKey('global_rate_limit', parseInt(e.target.value))}
                />
                <span className="text-[10px] opacity-20 font-black uppercase mb-1">req/min</span>
              </div>
            </div>

            <div className="bg-foreground/[0.01] border border-border p-6 rounded-[24px] space-y-3 flex flex-col justify-center">
              <div className="flex items-center space-x-4">
                <div className="relative inline-flex h-7 w-12 items-center rounded-full bg-foreground/[0.05] border border-border cursor-pointer transition-colors" onClick={() => updateKey('ddos_protection_enabled', !localConfig.ddos_protection_enabled)}>
                  <div className={clsx(
                    "absolute inset-0 rounded-full transition-colors duration-500",
                    localConfig.ddos_protection_enabled ? "bg-green-500/20" : "bg-red-500/10"
                  )} />
                  <span className={clsx(
                    "inline-block h-5 w-5 transform rounded-full transition-transform duration-500 shadow-lg relative z-10",
                    localConfig.ddos_protection_enabled ? "translate-x-6 bg-green-500" : "translate-x-1 bg-red-500/40"
                  )} />
                </div>
                <span className="text-[10px] opacity-40 uppercase font-black tracking-widest text-left">DDoS Mitigation</span>
              </div>
            </div>

            <div className="bg-foreground/[0.01] border border-border p-6 rounded-[24px] space-y-3 text-left">
              <label className="text-[9px] opacity-30 uppercase font-black tracking-widest block">Bot Username</label>
              <input 
                className="w-full bg-transparent border-b-2 border-border text-lg outline-none focus:border-primary/40 transition-all italic opacity-90 font-bold text-foreground" 
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
          className="flex items-center justify-center bg-primary text-primary-foreground h-16 w-16 rounded-[20px] shadow-2xl active:scale-90 transition-all"
        >
          {updateBatch.isPending ? <RefreshCw className="h-6 w-6 animate-spin" /> : <Save className="h-6 w-6" />}
        </button>
      </div>
    </div>
  );
}
