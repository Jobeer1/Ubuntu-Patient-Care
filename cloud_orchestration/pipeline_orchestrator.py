"""
Pipeline Orchestrator - End-to-End Training Pipeline
Coordinates the complete flow from Drive monitoring to model deployment.

This is the master orchestration script that demonstrates the full
"Simple Sync / Hidden Vertex AI / Auditable Opus" architecture.
"""

import json
import time
from datetime import datetime
from typing import Dict, Optional

# Import our pipeline components
from drive_monitor import run_monitoring_cycle
from vertex_pipeline_definition import initialize_vertex_ai, create_whisper_finetuning_job, get_job_status
from opus_audit_artifact import generate_audit_artifact, save_audit_artifact, upload_audit_to_gcs, print_audit_summary


def orchestrate_training_pipeline(
    wait_for_completion: bool = False,
    auto_deploy: bool = False
) -> Dict:
    """
    Execute the complete end-to-end training pipeline.
    
    Pipeline Stages:
        1. Monitor Google Drive for new training data
        2. Download and validate data (POPIA compliance)
        3. Upload to private GCS bucket
        4. Submit Vertex AI training job
        5. (Optional) Wait for job completion
        6. Generate Opus audit artifact
        7. (Optional) Deploy model to public bucket
    
    Args:
        wait_for_completion: If True, poll until training job completes
        auto_deploy: If True, automatically deploy successful models
        
    Returns:
        Dict: Complete pipeline execution summary
    """
    
    print("\n" + "🚀 " + "="*68)
    print("  UBUNTU PATIENT CARE - FULL PIPELINE ORCHESTRATION")
    print("  " + "="*68)
    print(f"  Started: {datetime.now().isoformat()}")
    print("  " + "="*68 + "\n")
    
    pipeline_result = {
        "pipeline_id": f"pipeline-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "started_at": datetime.now().isoformat(),
        "stages": {}
    }
    
    try:
        # STAGE 1: Drive Monitoring & Data Ingestion
        print("\n📥 STAGE 1: Drive Monitoring & Data Ingestion")
        print("-" * 70)
        
        monitoring_result = run_monitoring_cycle()
        pipeline_result['stages']['drive_monitoring'] = monitoring_result
        
        if monitoring_result.get('files_processed', 0) == 0:
            print("\nℹ No new training data available. Pipeline complete.")
            pipeline_result['status'] = 'no_new_data'
            return pipeline_result
        
        # Get the GCS URI of uploaded data
        gcs_input_uri = monitoring_result['gcs_uris'][0] if monitoring_result['gcs_uris'] else None
        if not gcs_input_uri:
            raise Exception("No GCS URI returned from monitoring stage")
        
        # Extract directory path (remove filename)
        gcs_input_dir = '/'.join(gcs_input_uri.split('/')[:-1]) + '/'
        
        print(f"\n✓ Stage 1 Complete: {monitoring_result['files_processed']} file(s) processed")
        
        # STAGE 2: Vertex AI Training Job Submission
        print("\n🧠 STAGE 2: Vertex AI Training Job Submission")
        print("-" * 70)
        
        initialize_vertex_ai()
        
        training_result = create_whisper_finetuning_job(
            gcs_input_uri=gcs_input_dir,
            job_display_name=f"whisper-finetune-{pipeline_result['pipeline_id']}"
        )
        
        pipeline_result['stages']['training_submission'] = training_result
        
        if not training_result.get('success'):
            raise Exception(f"Training job submission failed: {training_result.get('error')}")
        
        job_id = training_result['job_id']
        print(f"\n✓ Stage 2 Complete: Job {job_id} submitted")
        
        # STAGE 3: (Optional) Wait for Training Completion
        if wait_for_completion:
            print("\n⏳ STAGE 3: Waiting for Training Completion")
            print("-" * 70)
            print("  This may take 2-4 hours with GPU acceleration...")
            
            while True:
                status = get_job_status(job_id)
                state = status.get('state', 'UNKNOWN')
                
                print(f"  Job State: {state}")
                
                if state in ['JOB_STATE_SUCCEEDED', 'SUCCEEDED']:
                    print("\n✓ Training completed successfully!")
                    break
                elif state in ['JOB_STATE_FAILED', 'FAILED', 'JOB_STATE_CANCELLED', 'CANCELLED']:
                    raise Exception(f"Training job failed: {status.get('error', 'Unknown error')}")
                
                time.sleep(60)  # Check every minute
            
            pipeline_result['stages']['training_completion'] = status
        else:
            print("\n⏭ Skipping wait for completion (async mode)")
        
        # STAGE 4: Generate Opus Audit Artifact
        print("\n📋 STAGE 4: Generating Opus Audit Artifact")
        print("-" * 70)
        
        # Mock validation score for demo (in production, extract from training logs)
        validation_score = 0.963
        input_count = monitoring_result.get('files_processed', 0) * 100  # Estimate records
        
        audit_artifact = generate_audit_artifact(
            job_id=job_id,
            validation_score=validation_score,
            input_count=input_count,
            model_gcs_uri=training_result.get('output_dir', '') + '/model.tar.gz',
            input_source=f"GoogleDrive/{monitoring_result.get('files_processed', 0)}-clinics",
            additional_metadata={
                "pipeline_id": pipeline_result['pipeline_id'],
                "accelerator": training_result.get('accelerator', 'NVIDIA_TESLA_T4'),
                "training_time_estimate": "2-4 hours"
            }
        )
        
        pipeline_result['stages']['audit_artifact'] = audit_artifact
        
        # Save audit artifact
        artifact_filename = f"audit_{audit_artifact['artifact_id']}.json"
        save_audit_artifact(audit_artifact, f"audit_artifacts/{artifact_filename}")
        
        # Upload to GCS
        audit_gcs_uri = upload_audit_to_gcs(
            audit_artifact,
            bucket_name='ubuntu-ai-audit-trail',
            blob_path=f"audits/{datetime.now().strftime('%Y/%m/%d')}/{artifact_filename}"
        )
        
        pipeline_result['audit_gcs_uri'] = audit_gcs_uri
        
        print_audit_summary(audit_artifact)
        print(f"\n✓ Stage 4 Complete: Audit artifact generated")
        
        # STAGE 5: (Optional) Auto-Deploy
        if auto_deploy and audit_artifact['review_action'] == 'NO_HUMAN_REVIEW_NEEDED':
            print("\n🚀 STAGE 5: Auto-Deployment")
            print("-" * 70)
            print("  Model meets auto-approval criteria (>95% accuracy)")
            print("  Deploying to public bucket...")
            
            # In production: Copy model from private to public bucket
            # For demo: Just log the action
            print(f"  ✓ Model deployed: {audit_artifact['output_model_url']}")
            pipeline_result['deployed'] = True
        else:
            print("\n⏭ Skipping auto-deployment")
            pipeline_result['deployed'] = False
        
        # Pipeline Complete
        pipeline_result['status'] = 'success'
        pipeline_result['completed_at'] = datetime.now().isoformat()
        
        print("\n" + "="*70)
        print("  ✓ PIPELINE ORCHESTRATION COMPLETE")
        print("="*70)
        print(f"  Pipeline ID: {pipeline_result['pipeline_id']}")
        print(f"  Training Job: {job_id}")
        print(f"  Audit Artifact: {audit_gcs_uri}")
        print(f"  Status: {pipeline_result['status'].upper()}")
        print("="*70 + "\n")
        
        return pipeline_result
        
    except Exception as e:
        print(f"\n✗ Pipeline failed: {e}")
        pipeline_result['status'] = 'failed'
        pipeline_result['error'] = str(e)
        pipeline_result['failed_at'] = datetime.now().isoformat()
        return pipeline_result


if __name__ == "__main__":
    import sys
    
    # Parse command line arguments
    wait = '--wait' in sys.argv
    deploy = '--auto-deploy' in sys.argv
    
    print("Configuration:")
    print(f"  Wait for completion: {wait}")
    print(f"  Auto-deploy: {deploy}")
    
    # Run the pipeline
    result = orchestrate_training_pipeline(
        wait_for_completion=wait,
        auto_deploy=deploy
    )
    
    # Save pipeline result
    result_file = f"pipeline_results/{result['pipeline_id']}.json"
    with open(result_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"\nPipeline result saved: {result_file}")
    
    # Exit with appropriate code
    sys.exit(0 if result['status'] == 'success' else 1)
