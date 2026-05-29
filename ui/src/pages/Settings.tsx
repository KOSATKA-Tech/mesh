import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import axios from 'axios';
import { Save, Mail, Globe, Bell, Shield, RefreshCw } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function Settings() {
  const [localConfig, setLocalConfig] = useState<any>({});
  
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

  if (isLoading && Object.keys(localConfig).length === 0) return <div className="flex h-full items-center justify-center">Loading command center...</div>;

  return (
    <div className="space-y-8 max-w-4xl pb-24 lg:pb-0">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl lg:text-4xl font-bold tracking-tighter uppercase">Settings</h1>
          <p className="text-sm text-muted-foreground italic tracking-tight">Global Mesh Configuration & Parameters</p>
        </div>
        <button 
          onClick={handleSave}
          disabled={updateBatch.isPending}
          className="hidden sm:flex items-center space-x-2 bg-primary text-primary-foreground px-6 py-3 rounded-xl font-bold hover:opacity-90 transition-all shadow-lg shadow-primary/20"
        >
          {updateBatch.isPending ? <RefreshCw className="h-5 w-5 animate-spin" /> : <Save className="h-5 w-5" />}
          <span>{updateBatch.isPending ? 'Syncing...' : 'Save Changes'}</span>
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* SMTP Section */}
        <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} className="bg-card/50 border border-border p-6 rounded-2xl space-y-4 shadow-xl">
          <div className="flex items-center space-x-2 text-primary">
            <Mail className="h-5 w-5" />
            <h2 className="font-bold uppercase tracking-widest text-sm">SMTP RELAY</h2>
          </div>
          <div className="space-y-3 text-sm">
            <div className="space-y-1">
              <label className="text-[10px] text-muted-foreground uppercase font-bold tracking-tighter">Host</label>
              <input 
                className="w-full bg-background/50 border border-border rounded-lg p-2 text-sm outline-none focus:ring-1 focus:ring-primary transition-all" 
                value={localConfig.smtp_host || ''} 
                onChange={e => updateKey('smtp_host', e.target.value)}
                placeholder="smtp.example.com"
              />
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div className="col-span-1 space-y-1">
                <label className="text-[10px] text-muted-foreground uppercase font-bold tracking-tighter">Port</label>
                <input 
                  type="number"
                  className="w-full bg-background/50 border border-border rounded-lg p-2 text-sm outline-none focus:ring-1 focus:ring-primary transition-all" 
                  value={localConfig.smtp_port || 587} 
                  onChange={e => updateKey('smtp_port', parseInt(e.target.value))}
                />
              </div>
              <div className="col-span-2 space-y-1">
                <label className="text-[10px] text-muted-foreground uppercase font-bold tracking-tighter">From Email</label>
                <input 
                  className="w-full bg-background/50 border border-border rounded-lg p-2 text-sm outline-none focus:ring-1 focus:ring-primary transition-all" 
                  value={localConfig.smtp_from || ''} 
                  onChange={e => updateKey('smtp_from', e.target.value)}
                  placeholder="admin@mesh.local"
                />
              </div>
            </div>
            <div className="space-y-1">
              <label className="text-[10px] text-muted-foreground uppercase font-bold tracking-tighter">Username</label>
              <input 
                className="w-full bg-background/50 border border-border rounded-lg p-2 text-sm outline-none focus:ring-1 focus:ring-primary transition-all" 
                value={localConfig.smtp_user || ''} 
                onChange={e => updateKey('smtp_user', e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <label className="text-[10px] text-muted-foreground uppercase font-bold tracking-tighter">Password</label>
              <input 
                type="password"
                className="w-full bg-background/50 border border-border rounded-lg p-2 text-sm outline-none focus:ring-1 focus:ring-primary transition-all" 
                value={localConfig.smtp_password || ''} 
                onChange={e => updateKey('smtp_password', e.target.value)}
              />
            </div>
          </div>
        </motion.div>

        {/* DNS Automation Section */}
        <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="bg-card/50 border border-border p-6 rounded-2xl space-y-4 shadow-xl">
          <div className="flex items-center space-x-2 text-primary">
            <Globe className="h-5 w-5" />
            <h2 className="font-bold uppercase tracking-widest text-sm">DNS AUTOMATION</h2>
          </div>
          <div className="space-y-3">
             <div className="space-y-1">
              <label className="text-[10px] text-muted-foreground uppercase font-bold tracking-tighter">Base Domain</label>
              <input 
                className="w-full bg-background/50 border border-border rounded-lg p-2 text-sm outline-none focus:ring-1 focus:ring-primary transition-all" 
                value={localConfig.base_domain || ''} 
                onChange={e => updateKey('base_domain', e.target.value)}
                placeholder="ub.kosatka.tech"
              />
            </div>
            <div className="space-y-1">
              <label className="text-[10px] text-muted-foreground uppercase font-bold tracking-tighter">DNS Provider</label>
              <select 
                className="w-full bg-background/50 border border-border rounded-lg p-2 text-sm outline-none focus:ring-1 focus:ring-primary appearance-none transition-all cursor-pointer"
                value={localConfig.dns_provider || 'manual'}
                onChange={e => updateKey('dns_provider', e.target.value)}
              >
                <option value="manual">Manual / No API</option>
                <option value="cloudflare">Cloudflare</option>
                <option value="digitalocean">DigitalOcean</option>
                <option value="hetzner">Hetzner</option>
                <option value="beget">Beget API</option>
                <option value="route53">AWS Route53</option>
                <option value="google">Google Cloud DNS</option>
              </select>
            </div>
            
            <AnimatePresence mode="wait">
              {localConfig.dns_provider === 'cloudflare' && (
                <motion.div key="cf" initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} className="space-y-3 pt-2">
                  <div className="space-y-1">
                    <label className="text-[10px] text-muted-foreground uppercase font-bold tracking-tighter">API Token</label>
                    <input type="password" title="API Token" className="w-full bg-background/50 border border-border rounded-lg p-2 text-sm outline-none focus:ring-1 focus:ring-primary" value={localConfig.cloudflare_token || ''} onChange={e => updateKey('cloudflare_token', e.target.value)} />
                  </div>
                  <div className="space-y-1">
                    <label className="text-[10px] text-muted-foreground uppercase font-bold tracking-tighter">Zone ID</label>
                    <input className="w-full bg-background/50 border border-border rounded-lg p-2 text-sm outline-none focus:ring-1 focus:ring-primary" value={localConfig.cloudflare_zone_id || ''} onChange={e => updateKey('cloudflare_zone_id', e.target.value)} />
                  </div>
                </motion.div>
              )}

              {localConfig.dns_provider === 'digitalocean' && (
                <motion.div key="do" initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} className="space-y-3 pt-2">
                  <div className="space-y-1">
                    <label className="text-[10px] text-muted-foreground uppercase font-bold tracking-tighter">Personal Access Token</label>
                    <input type="password" title="PAT" className="w-full bg-background/50 border border-border rounded-lg p-2 text-sm outline-none focus:ring-1 focus:ring-primary" value={localConfig.do_token || ''} onChange={e => updateKey('do_token', e.target.value)} />
                  </div>
                </motion.div>
              )}

              {localConfig.dns_provider === 'hetzner' && (
                <motion.div key="hetzner" initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} className="space-y-3 pt-2">
                  <div className="space-y-1">
                    <label className="text-[10px] text-muted-foreground uppercase font-bold tracking-tighter">API Token</label>
                    <input type="password" title="API Token" className="w-full bg-background/50 border border-border rounded-lg p-2 text-sm outline-none focus:ring-1 focus:ring-primary" value={localConfig.hetzner_token || ''} onChange={e => updateKey('hetzner_token', e.target.value)} />
                  </div>
                </motion.div>
              )}

              {localConfig.dns_provider === 'beget' && (
                <motion.div key="beget" initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} className="space-y-3 pt-2">
                  <div className="space-y-1">
                    <label className="text-[10px] text-muted-foreground uppercase font-bold tracking-tighter">Beget Login</label>
                    <input className="w-full bg-background/50 border border-border rounded-lg p-2 text-sm outline-none focus:ring-1 focus:ring-primary" value={localConfig.beget_login || ''} onChange={e => updateKey('beget_login', e.target.value)} />
                  </div>
                  <div className="space-y-1">
                    <label className="text-[10px] text-muted-foreground uppercase font-bold tracking-tighter">Beget API Key</label>
                    <input type="password" title="API Key" className="w-full bg-background/50 border border-border rounded-lg p-2 text-sm outline-none focus:ring-1 focus:ring-primary" value={localConfig.beget_api_key || ''} onChange={e => updateKey('beget_api_key', e.target.value)} />
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </motion.div>

        {/* Monitoring Thresholds */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="bg-card/50 border border-border p-6 rounded-2xl space-y-4 shadow-xl">
          <div className="flex items-center space-x-2 text-primary">
            <Bell className="h-5 w-5" />
            <h2 className="font-bold uppercase tracking-widest text-sm">MONITORING ALERTS</h2>
          </div>
          <div className="space-y-3">
             <div className="flex justify-between items-center bg-background/30 p-3 rounded-xl">
              <label className="text-xs text-muted-foreground uppercase font-bold">CPU Alert Threshold (%)</label>
              <input 
                type="number"
                className="w-16 bg-transparent border-b border-border text-sm outline-none text-right font-bold focus:border-primary transition-all" 
                value={localConfig.cpu_alert_threshold || 90} 
                onChange={e => updateKey('cpu_alert_threshold', parseInt(e.target.value))}
              />
            </div>
            <div className="flex justify-between items-center bg-background/30 p-3 rounded-xl">
              <label className="text-xs text-muted-foreground uppercase font-bold">RAM Alert Threshold (%)</label>
              <input 
                type="number"
                className="w-16 bg-transparent border-b border-border text-sm outline-none text-right font-bold focus:border-primary transition-all" 
                value={localConfig.ram_alert_threshold || 90} 
                onChange={e => updateKey('ram_alert_threshold', parseInt(e.target.value))}
              />
            </div>
            <div className="flex justify-between items-center bg-background/30 p-3 rounded-xl">
              <label className="text-xs text-muted-foreground uppercase font-bold">Temp Alert Threshold (°C)</label>
              <input 
                type="number"
                className="w-16 bg-transparent border-b border-border text-sm outline-none text-right font-bold focus:border-primary transition-all" 
                value={localConfig.temp_alert_threshold || 80} 
                onChange={e => updateKey('temp_alert_threshold', parseInt(e.target.value))}
              />
            </div>
          </div>
        </motion.div>

        {/* Security Section */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="bg-card/50 border border-border p-6 rounded-2xl space-y-4 shadow-xl">
          <div className="flex items-center space-x-2 text-primary">
            <Shield className="h-5 w-5" />
            <h2 className="font-bold uppercase tracking-widest text-sm">GLOBAL SECURITY</h2>
          </div>
          <div className="space-y-3">
            <div className="flex justify-between items-center bg-background/30 p-3 rounded-xl">
              <label className="text-xs text-muted-foreground uppercase font-bold">Rate Limit (req/min)</label>
              <input 
                type="number"
                className="w-16 bg-transparent border-b border-border text-sm outline-none text-right font-bold focus:border-primary transition-all" 
                value={localConfig.global_rate_limit || 60} 
                onChange={e => updateKey('global_rate_limit', parseInt(e.target.value))}
              />
            </div>
            <div className="flex items-center space-x-3 p-2">
              <input 
                type="checkbox" 
                id="ddos_active"
                className="h-5 w-5 rounded border-border bg-background text-primary focus:ring-primary cursor-pointer transition-all"
                checked={localConfig.ddos_protection_enabled ?? true}
                onChange={e => updateKey('ddos_protection_enabled', e.target.checked)}
              />
              <label htmlFor="ddos_active" className="text-xs text-muted-foreground uppercase font-bold cursor-pointer">Enable Network DDoS Protection</label>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Mobile Floating Action Button */}
      <div className="sm:hidden fixed bottom-6 right-6 z-50">
        <button 
          onClick={handleSave}
          disabled={updateBatch.isPending}
          className="flex items-center justify-center bg-primary text-primary-foreground h-16 w-16 rounded-full font-bold shadow-[0_0_30px_rgba(255,255,255,0.2)] active:scale-90 transition-all border-4 border-background"
        >
          {updateBatch.isPending ? <RefreshCw className="h-7 w-7 animate-spin" /> : <Save className="h-7 w-7" />}
        </button>
      </div>
    </div>
  );
}
