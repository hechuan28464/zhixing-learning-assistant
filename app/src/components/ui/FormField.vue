<script setup>
import {computed,nextTick,useId} from 'vue'
import {useField} from 'vee-validate'
const props=defineProps({name:String,label:String,hint:String,as:{type:String,default:'input'},type:{type:String,default:'text'},rows:{type:Number,default:4},maxlength:Number,required:Boolean,disabled:Boolean,placeholder:String,autocomplete:{type:String,default:'off'}})
const uid=useId(),controlId='field-'+uid
const {value,errorMessage,meta,handleChange,handleBlur,validate}=useField(()=>props.name,undefined,{validateOnValueUpdate:false})
const showError=computed(()=>meta.touched&&!!errorMessage.value)
const describedBy=computed(()=>[props.hint?controlId+'-hint':'',showError.value?controlId+'-error':''].filter(Boolean).join(' ')||undefined)
function change(event){if(event.isComposing)return;handleChange(event,false);if(meta.touched)nextTick(validate)}
</script>
<template><div :class="['studio-field',{invalid:showError}]"><div class="studio-field-label"><label :for="controlId">{{ label }} <span v-if="required" aria-hidden="true">必填</span></label><small v-if="maxlength">{{ String(value??'').length }}/{{ maxlength }}</small></div><component :is="as" :id="controlId" :name="name" :type="as==='input'?type:undefined" :value="value" :rows="as==='textarea'?rows:undefined" :maxlength="maxlength" :required="required" :disabled="disabled" :placeholder="placeholder" :autocomplete="autocomplete" :aria-invalid="showError?'true':undefined" :aria-describedby="describedBy" class="studio-field-control" @input="change" @compositionend="change" @blur="handleBlur($event,true)"/><p v-if="showError" :id="controlId+'-error'" class="studio-field-error" role="alert">{{ errorMessage }}</p><p v-else-if="hint" :id="controlId+'-hint'" class="studio-field-hint">{{ hint }}</p></div></template>
