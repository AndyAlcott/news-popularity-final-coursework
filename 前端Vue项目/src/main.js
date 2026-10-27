import Vue from 'vue';
import ElementUI from 'element-ui';
import 'element-ui/lib/theme-chalk/index.css';
Vue.use(ElementUI);

new Vue({
  el:'#app',
  data:{user:'', password:'', authenticated:false, page:'predict', csrf:{}, schema:{features:[],labels:[]}, features:{}, model:'random_forest', result:null, records:[], metrics:null, figure:'01_class_distribution', busy:false},
  async mounted(){ await this.token(); try { await this.request('/api/auth/me'); this.authenticated=true; await this.load(); } catch(e) {} },
  methods:{
    async token(){ this.csrf=await (await fetch('/api/csrf')).json(); },
    async request(url,options={}) {
      options.headers={...(options.headers||{}),[this.csrf.header]:this.csrf.token};
      const response=await fetch(url,options);
      if(!response.ok){ let message='请求失败，请检查服务及输入'; try {message=(await response.json()).error||message} catch(e){} throw new Error(message); }
      return response.status===204 ? null : response.json();
    },
    async login(){
      if(!this.user || !this.password){this.$message.warning('请输入账号和密码');return;}
      const response=await fetch('/login',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded',[this.csrf.header]:this.csrf.token},body:new URLSearchParams({username:this.user,password:this.password})});
      if(!response.ok){ this.$message.error('账号或密码错误'); await this.token(); return; }
      this.password=''; this.authenticated=true; await this.token(); await this.load();
    },
    async logout(){await fetch('/logout',{method:'POST',headers:{[this.csrf.header]:this.csrf.token}}); this.authenticated=false; this.result=null; await this.token();},
    async load(){try {this.schema=await this.request('/api/schema'); await this.sample();} catch(e){this.$message.error(e.message)}},
    async sample(){try {let value=await this.request('/api/sample'); this.features=value.features;} catch(e){this.$message.error(e.message)}},
    async go(page){this.page=page; try {if(page==='records') this.records=await this.request('/api/records'); if(page==='analysis') this.metrics=await this.request('/api/metrics');} catch(e){this.$message.error(e.message)}},
    async predict(){
      if(this.schema.features.some(k=>this.features[k]===null||this.features[k]===undefined||this.features[k]===''||!Number.isFinite(Number(this.features[k])))){this.$message.warning('请完整填写有效数值');return;}
      this.busy=true;
      try {this.result=await this.request('/api/predict',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model:this.model,features:this.features})}); this.$message.success('预测成功，记录已保存');} catch(e){this.$message.error(e.message)} finally {this.busy=false;}
    },
    async remove(id){try {await this.$confirm('确定删除这条预测记录？','提示',{type:'warning'}); await this.request('/api/records/'+id,{method:'DELETE'}); await this.go('records'); this.$message.success('已删除');}catch(e){if(e!=='cancel'&&e!=='close')this.$message.error(e.message||'删除失败')}},
    percent(n){return (Number(n)*100).toFixed(2)+'%';}
  }
});
