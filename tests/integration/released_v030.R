# Run with an existing Neoantimon2 v0.3.0 library. No predictor or network.
# Rscript tests/integration/released_v030.R /path/to/registry /path/to/new/run-output
args<-commandArgs(TRUE);registry_root<-normalizePath(args[[1L]]);out<-args[[2L]]
stopifnot(!dir.exists(out));dir.create(out,recursive=TRUE);out<-normalizePath(out)
library(Neoantimon2)
stopifnot(as.character(packageVersion('Neoantimon2'))=='0.3.0')
package<-packageDescription('Neoantimon2')
if(!is.null(package$RemoteSha))stopifnot(package$RemoteSha=='eca5f06fc39c1275f1e4f47ba3886f532fb08a6b')
# Reuse only the installed technical references and configuration construction.
e<-new.env();source(system.file('examples/quickstart.R',package='Neoantimon2'),local=e)
inputs_dir<-file.path(out,'inputs');dir.create(inputs_dir)
v<-file.path(inputs_dir,'synthetic.vcf')
writeLines(c('##fileformat=VCFv4.2','##FORMAT=<ID=GT,Number=1,Type=String,Description=Genotype>',
 '#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tsample-1',
 'chrF\t4\t.\tA\tC\t.\tPASS\t.\tGT\t0/1','chrW\t4\t.\tA\tC\t.\tPASS\t.\tGT\t0/1','chrO\t7\t.\tC\tT\t.\tPASS\t.\tGT\t0/1'),v)
cfg<-neo_config(env=character(),paths=list(data_root=inputs_dir,input_root=inputs_dir,run_root=file.path(out,'runs')),
 resources=e$cfg$resources,scientific=e$cfg$scientific,checksum='sha256',
 peptides=list(class_i_lengths=9L,class_ii_lengths=9L))
hla<-c('HLA-A*02:01','HLA-B*07:02','HLA-DRA*01:01~HLA-DRB1*15:01',
 'HLA-DPA1*02:01~HLA-DPB1*01:01','HLA-DQA1*01:02~HLA-DQB1*06:02')
p<-neo_run(neo_project(samples=data.frame(sample_id='sample-1',patient_id='synthetic-subject'),config=cfg,
 hla=list('synthetic-subject'=hla),inputs=list(list(input_id='technical-variants',input_role='somatic_vcf',sample_id='sample-1',path=v))))
native<-neo_results(p);origins<-neo_origins(p);events<-neo_events(p)
stopifnot(nrow(native)==10L,nrow(origins)==3L,nrow(events)==3L,max(native$n_origins)==2L,
 all(native$grading_status=='NOT_GRADED'),all(native$prediction_status=='NOT_RUN'))
bundle<-neo_export_bundle(p,dir=file.path(out,'export'))
peptides<-sort(unique(native$ligand_sequence));stopifnot(length(peptides)==2L)
original_files<-list.files(p$path,recursive=TRUE,full.names=TRUE)
hash<-function(f)digest::digest(file=f,algo='sha256',serialize=FALSE)
original_hashes<-vapply(original_files,hash,'')
native_explanations<-lapply(native$candidate_id,function(id)neo_explain(p,candidate_id=id))
index<-file.path(registry_root,'index.json');specs<-jsonlite::read_json(file.path(registry_root,'tools/converter_specs.json'))
summary<-list();analyses<-list()
for(s in specs) {
 id<-s$id;dir<-file.path(out,id);dir.create(dir)
 lines<-readLines(file.path(registry_root,'converters',id,'input-X.tsv'))
 # Replace only invented fixture peptides by the two real synthetic project queries.
 lines<-gsub('SIINFEKLA',peptides[[1L]],lines,fixed=TRUE)
 lines<-gsub('NLVPMVATV',peptides[[2L]],lines,fixed=TRUE)
 # EL and IM use opposing synthetic values on the same queries to prove independence.
 if(id=='bigmhc-im@1.0.0') {
  lines<-gsub(',0$',',0.99',lines);lines<-gsub(',0.875$',',0.01',lines)
  lines<-gsub(',0.25$',',0.8',lines);lines<-gsub(',0.5$',',0.1',lines)
 }
 if(id=='mixmhc2pred-el@1.0.0') {
  # A real matched query gets a documented native NA status, independent of the
  # extra unsupported 8-mer query that must be retained in unmatched.tsv.
  i<-which(startsWith(lines,paste0(peptides[[1L]],'\t')))[[1L]]
  h<-strsplit(lines[which(startsWith(lines,'Peptide\t'))],'\t',fixed=TRUE)[[1L]]
  cells<-strsplit(lines[[i]],'\t',fixed=TRUE)[[1L]];cells[[match('%Rank_DRB1_15_01',h)]]<-'NA';lines[[i]]<-paste(cells,collapse='\t')
 }
 input<-file.path(dir,'native-output.tsv');writeLines(lines,input)
 metric<-if(id=='prime-im@1.0.0')'immunogenicity_percentile' else if(s$parser=='wide')'presentation_percentile' else s$metrics[[1L]][[2L]]
 direction<-if(s$parser=='wide'||s$category=='BA')'lower_is_better' else 'higher_is_better'
 policy<-list(mode='external_rank',provider=s$provider,run_id=paste0('input-sha256:',hash(input)),
  task=s$task,metric=metric,score_direction=direction)
 a<-neo_analyze_external(p,input,policy,converter_id=id,registry=index,trust=TRUE)
 r<-neo_external_results(a);expected_class<-s$class
 unmatched<-read.delim(file.path(a$path,'unmatched.tsv'),colClasses='character')
 stopifnot(nrow(unmatched)==if(expected_class=='II')3L else 0L)
 selected<-r$hla_class==expected_class;stopifnot(nrow(r)==10L,sum(selected)==if(expected_class=='I')4L else 6L)
 stopifnot(all(r$external_status[!selected]=='NOT_PREDICTED'),all(is.na(r$external_rank[!selected])))
 if(expected_class=='I')stopifnot(all(r$external_status[selected]=='evaluated'),all(!is.na(r$external_rank[selected])))
 if(expected_class=='II')stopifnot(sum(r$external_status=='unsupported')==1L,sum(r$external_status=='evaluated')==5L,
   all(is.na(r$external_score[r$external_status=='unsupported'])),all(is.na(r$external_rank[r$external_status=='unsupported'])))
 checks<-list()
 for(i in which(selected)) {
  xp<-neo_external_explain(a,r$candidate_id[[i]])
  c<-xp$candidates[[1L]]
  n<-which(native$candidate_id==r$candidate_id[[i]])
  stopifnot(setequal(vapply(c$origins,`[[`,'','origin_id'),unlist(native$origin_ids[[n]])))
  evidence<-r$external_evidence[[i]]
  stopifnot(length(evidence)>0L,all(vapply(evidence,function(z)z$mhc_key==native$mhc_key[[n]]&&z$peptide_sequence==native$ligand_sequence[[n]]&&z$provider==s$provider,TRUE)))
  selected_evidence<-Filter(function(z)z$metric==metric,evidence);stopifnot(length(selected_evidence)==1L)
  z<-selected_evidence[[1L]];stopifnot(z$score_direction==direction)
  if(z$status=='evaluated')stopifnot(r$external_score[[i]]==as.numeric(z$score))
  if(s$category=='IM')stopifnot(z$metric_semantics %in% c('raw','external_percentile'),!z$metric_semantics %in% c('mhc_binding_percentile','mhc_presentation_percentile'))
  checks[[length(checks)+1L]]<-list(candidate_id=r$candidate_id[[i]],peptide=native$ligand_sequence[[n]],mhc_key=native$mhc_key[[n]],origins=length(c$origins),status=z$status,metric=z$metric,unit=z$unit,direction=z$score_direction,source_row=z$source_row)
 }
 ready<-r[r$external_status=='evaluated'&selected,,drop=FALSE]
 for(cl in unique(ready$hla_class)) {
  t<-ready[ready$hla_class==cl,,drop=FALSE];sorter<-if(direction=='higher_is_better')-t$external_score else t$external_score
  ord<-order(sorter,t$candidate_id);stopifnot(identical(as.integer(t$external_rank[ord]),seq_len(nrow(t))))
 }
 stopifnot(identical(neo_results(p),native),identical(neo_events(p),events),identical(neo_origins(p),origins),
  identical(lapply(native$candidate_id,function(id)neo_explain(p,candidate_id=id)),native_explanations),
  identical(vapply(original_files,hash,''),original_hashes),!any(grepl('external_final_grade',names(r))))
 stopifnot(identical(neo_external_results(a$analysis_id,project=neo_project(path=p$path)),r))
 # Compare to direct standalone output and validate every static expected fixture
 # through the authoritative released standard reader, without changing core.
 fixture<-file.path(registry_root,'converters',id,'expected.tsv');Neoantimon2:::external_read_predictions(fixture)
 command<-c(shQuote(file.path(registry_root,'converters',id,'converter.py')),'--input',shQuote(input),'--output',shQuote(file.path(dir,'standard.tsv')),'--bundle',shQuote(bundle$path))
 stopifnot(system2(Sys.which('python3'),command)==0L)
 normalized<-Neoantimon2:::external_read_predictions(file.path(dir,'standard.tsv'))
 if(s$category=='IM') {
  wrong<-policy;wrong$mode<-'somatic_grade';wrong$hla_class<-'I'
  err<-tryCatch({neo_analyze_external(p,file.path(dir,'standard.tsv'),wrong);NULL},error=conditionMessage)
  stopifnot(!is.null(err),grepl('GRADING_PREREQUISITES',err))
 }
 write.csv(r[,c('candidate_id','ligand_sequence','mhc_key','external_status','external_score','external_rank')],file.path(dir,'external-results.csv'),row.names=FALSE)
 jsonlite::write_json(checks,file.path(dir,'explanation-provenance.json'),pretty=TRUE,auto_unbox=TRUE)
 summary[[id]]<-list(converter=id,category=s$category,status='CONVERTER_AND_IMPORT_VALIDATED_WITH_SCHEMA_FAITHFUL_FIXTURE',
  imported_rows=nrow(normalized),unmatched_rows=nrow(unmatched),matched_candidates=sum(selected),evaluated=sum(r$external_status=='evaluated'),unsupported=sum(r$external_status=='unsupported'),
  not_predicted=sum(r$external_status=='NOT_PREDICTED'),all_origins_preserved=TRUE,native_unchanged=TRUE,
  analysis_id=a$analysis_id,analysis_path=a$path,metric=metric,direction=direction)
 analyses[[id]]<-r
}
el<-analyses[['bigmhc-el@1.0.0']];im<-analyses[['bigmhc-im@1.0.0']]
stopifnot(identical(el$candidate_id,im$candidate_id),!identical(el$external_score,im$external_score),!identical(el$external_rank,im$external_rank),
 summary[['bigmhc-el@1.0.0']]$analysis_id!=summary[['bigmhc-im@1.0.0']]$analysis_id)
jsonlite::write_json(list(status='PASS',predictor_execution=FALSE,validation='CONVERTER_AND_IMPORT_VALIDATED_WITH_SCHEMA_FAITHFUL_FIXTURE',
 package_version='0.3.0',package_commit=package$RemoteSha,package_path=find.package('Neoantimon2'),
 events=nrow(events),origins=nrow(origins),candidates=nrow(native),max_origins_per_candidate=max(native$n_origins),
 HLA=hla,converters=summary,BA_demo='mhcflurry-ba@1.0.0',EL_demo='bigmhc-el@1.0.0',IM_demo='bigmhc-im@1.0.0',
 EL_IM_separate_analyses=TRUE,EL_IM_distinct_rankings=TRUE,native_results_unchanged=TRUE,all_original_files_unchanged=TRUE,
 project=p$path,export_bundle=bundle$path),file.path(out,'integration-results.json'),pretty=TRUE,auto_unbox=TRUE)
cat('PASS: nine Registry converters, BA/EL/IM and independent EL+IM; no predictor execution.\n')
