import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import axios from 'axios';
import { Save, Mail, Globe, Bell, Shield } from 'lucide-react';
import { motion } from 'framer-motion';

export default function Settings() {
  const { data: configs, isLoading } = useQuery({
    queryKey: ['system-configs'],
    queryFn: async () => {
      const resp = await axios.get('/api/v1/config/');
      // Convert list to object for easier handling
      const obj: any = {};
      resp.data.forEach((c: any) => {
        try {
          obj[c.key] = JSON.parse(c.value);
        } catch {
          obj[c.key] = c.value;
        }
      });
      return obj;
    }
  });

  const [localConfig, setLocalConfig] = useState<any>({});
  
  // Update local state when query finishes
  React.useEffect(() => {
    if (configs) setLocalConfig(configs);
  }, [configs]);

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

  if (isLoading) return <div>Loading command center...</div>;

  return (
    <div className="space-y-8 max-w-4xl">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-4xl font-bold tracking-tighter">SETTINGS</h1>
          <p className="text-muted-foreground italic">Global Mesh Configuration & Parameters</p>
        </div>
        <button 
          onClick={handleSave}
          disabled={updateBatch.isPending}
          className="flex items-center space-x-2 bg-primary text-primary-foreground px-6 py-3 rounded-xl font-bold hover:opacity-90 transition-all shadow-lg shadow-primary/20"
        >
          <Save className="h-5 w-5" />
          <span>{updateBatch.isPending ? 'Syncing...' : 'Save Changes'}</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* SMTP Section */}
        <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} className="bg-card/50 border border-border p-6 rounded-2xl space-y-4">
          <div className="flex items-center space-x-2 text-primary">
            <Mail className="h-5 w-5" />
            <h2 className="font-bold uppercase tracking-widest text-sm">SMTP RELAY</h2>
          </div>
          <div className="space-y-3">
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground uppercase font-bold">Host</label>
              <input 
                className="w-full bg-background/50 border border-border rounded-lg p-2 text-sm outline-none focus:ring-1 focus:ring-primary" 
                value={localConfig.smtp_host || ''} 
                onChange={e => updateKey('smtp_host', e.target.value)}
                placeholder="smtp.example.com"
              />
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div className="col-span-1 space-y-1">
                <label className="text-xs text-muted-foreground uppercase font-bold">Port</label>
                <input 
                  type="number"
                  className="w-full bg-background/50 border border-border rounded-lg p-2 text-sm outline-none focus:ring-1 focus:ring-primary" 
                  value={localConfig.smtp_port || 587} 
                  onChange={e => updateKey('smtp_port', parseInt(e.target.value))}
                />
              </div>
              <div className="col-span-2 space-y-1">
                <label className="text-xs text-muted-foreground uppercase font-bold">From Email</label>
                <input 
                  className="w-full bg-background/50 border border-border rounded-lg p-2 text-sm outline-none focus:ring-1 focus:ring-primary" 
                  value={localConfig.smtp_from || ''} 
                  onChange={e => updateKey('smtp_from', e.target.value)}
                  placeholder="admin@mesh.local"
                />
              </div>
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground uppercase font-bold">Username</label>
              <input 
                className="w-full bg-background/50 border border-border rounded-lg p-2 text-sm outline-none focus:ring-1 focus:ring-primary" 
                value={localConfig.smtp_user || ''} 
                onChange={e => updateKey('smtp_user', e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground uppercase font-bold">Password</label>
              <input 
                type="password"
                className="w-full bg-background/50 border border-border rounded-lg p-2 text-sm outline-none focus:ring-1 focus:ring-primary" 
                value={localConfig.smtp_password || ''} 
                onChange={e => updateKey('smtp_password', e.target.value)}
              />
            </div>
          </div>
        </motion.div>

        {/* DNS Automation Section */}
        <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="bg-card/50 border border-border p-6 rounded-2xl space-y-4">
          <div className="flex items-center space-x-2 text-primary">
            <Globe className="h-5 w-5" />
            <h2 className="font-bold uppercase tracking-widest text-sm">DNS AUTOMATION</h2>
          </div>
          <div className="space-y-3">
             <div className="space-y-1">
              <label className="text-xs text-muted-foreground uppercase font-bold">Base Domain</label>
              <input 
                className="w-full bg-background/50 border border-border rounded-lg p-2 text-sm outline-none focus:ring-1 focus:ring-primary" 
                value={localConfig.base_domain || ''} 
                onChange={e => updateKey('base_domain', e.target.value)}
                placeholder="ub.kosatka.tech"
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground uppercase font-bold">DNS Provider</label>
              <select 
                className="w-full bg-background/50 border border-border rounded-lg p-2 text-sm outline-none focus:ring-1 focus:ring-primary"
                value={localConfig.dns_provider || 'manual'}
                onChange={e => updateKey('dns_provider', e.target.value)}
              >
                <option value="manual">Manual / No API</option>
                <option value="beget">Beget API</option>
                <option value="cloudflare">Cloudflare (Soon)</option>
              </select>
            </div>
            {localConfig.dns_provider === 'beget' && (
              <>
                <div className="space-y-1">
                  <label className="text-xs text-muted-foreground uppercase font-bold">Beget Login</label>
                  <input 
                    className="w-full bg-background/50 border border-border rounded-lg p-2 text-sm outline-none focus:ring-1 focus:ring-primary" 
                    value={localConfig.beget_login || ''} 
                    onChange={e => updateKey('beget_login', e.target.value)}
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-muted-foreground uppercase font-bold">Beget API Key</label>
                  <input 
                    type="password"
                    className="w-full bg-background/50 border border-border rounded-lg p-2 text-sm outline-none focus:ring-1 focus:ring-primary" 
                    value={localConfig.beget_api_key || ''} 
                    onChange={e => updateKey('beget_api_key', e.target.value)}
                  />
                </div>
              </>
            )}
          </div>
        </motion.div>

        {/* Monitoring Thresholds */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="bg-card/50 border border-border p-6 rounded-2xl space-y-4">
          <div className="flex items-center space-x-2 text-primary">
            <Bell className="h-5 w-5" />
            <h2 className="font-bold uppercase tracking-widest text-sm">MONITORING ALERTS</h2>
          </div>
          <div className="space-y-3">
             <div className="flex justify-between items-center">
              <label className="text-xs text-muted-foreground uppercase font-bold">CPU Alert Threshold (%)</label>
              <input 
                type="number"
                className="w-20 bg-background/50 border border-border rounded-lg p-2 text-sm outline-none text-right" 
                value={localConfig.cpu_alert_threshold || 90} 
                onChange={e => updateKey('cpu_alert_threshold', parseInt(e.target.value))}
              />
            </div>
            <div className="flex justify-between items-center">
              <label className="text-xs text-muted-foreground uppercase font-bold">RAM Alert Threshold (%)</label>
              <input 
                type="number"
                className="w-20 bg-background/50 border border-border rounded-lg p-2 text-sm outline-none text-right" 
                value={localConfig.ram_alert_threshold || 90} 
                onChange={e => updateKey('ram_alert_threshold', parseInt(e.target.value))}
              />
            </div>
            <div className="flex justify-between items-center">
              <label className="text-xs text-muted-foreground uppercase font-bold">Temp Alert Threshold (°C)</label>
              <input 
                type="number"
                className="w-20 bg-background/50 border border-border rounded-lg p-2 text-sm outline-none text-right" 
                value={localConfig.temp_alert_threshold || 80} 
                onChange={e => updateKey('temp_alert_threshold', parseInt(e.target.value))}
              />
            </div>
          </div>
        </motion.div>

        {/* Security Section */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="bg-card/50 border border-border p-6 rounded-2xl space-y-4">
          <div className="flex items-center space-x-2 text-primary">
            <Shield className="h-5 w-5" />
            <h2 className="font-bold uppercase tracking-widest text-sm">GLOBAL SECURITY</h2>
          </div>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <label className="text-xs text-muted-foreground uppercase font-bold">Rate Limit (req/min)</label>
              <input 
                type="number"
                className="w-20 bg-background/50 border border-border rounded-lg p-2 text-sm outline-none text-right" 
                value={localConfig.global_rate_limit || 60} 
                onChange={e => updateKey('global_rate_limit', parseInt(e.target.value))}
              />
            </div>
            <div className="flex items-center space-x-3">
              <input 
                type="checkbox" 
                id="ddos_active"
                className="h-4 w-4 rounded border-border bg-background"
                checked={localConfig.ddos_protection_enabled ?? true}
                onChange={e => updateKey('ddos_protection_enabled', e.target.checked)}
              />
              <label htmlFor="ddos_active" className="text-xs text-muted-foreground uppercase font-bold">Enable Network DDoS Protection</label>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
