import {publicPrivacyDetails} from '../lib/privacy.js';
import {json} from '../lib/admin-auth.js';

// Only the publication-ready legal identity is returned; never partial details.
export default function handler(req,res){
 res.setHeader('X-Robots-Tag','noindex, noarchive');
 if(req.method!=='GET')return json(res,405,{error:'Método no permitido'});
 const identity=publicPrivacyDetails();
 if(!identity)return json(res,200,{ready:false});
 return json(res,200,{ready:true,...identity});
}
