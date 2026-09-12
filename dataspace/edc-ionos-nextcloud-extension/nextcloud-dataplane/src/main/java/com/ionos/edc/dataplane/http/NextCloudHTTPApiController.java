package com.ionos.edc.dataplane.http;

import com.ionos.edc.http.HttpParts;
import com.ionos.edc.nextcloudapi.NextCloudApi;
import io.swagger.v3.oas.annotations.parameters.RequestBody;
import jakarta.ws.rs.Consumes;
import jakarta.ws.rs.POST;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.Produces;
import jakarta.ws.rs.core.MediaType;
import org.eclipse.edc.connector.controlplane.transfer.spi.store.TransferProcessStore;
import org.eclipse.edc.connector.controlplane.transfer.spi.types.TransferProcess;
import org.eclipse.edc.connector.controlplane.transfer.spi.types.TransferProcessStates;
import org.eclipse.edc.connector.dataplane.spi.pipeline.PipelineService;
import org.eclipse.edc.spi.result.StoreResult;
import org.eclipse.edc.spi.security.Vault;
import org.eclipse.edc.spi.types.TypeManager;
import org.eclipse.edc.spi.monitor.Monitor;
import org.eclipse.edc.spi.types.domain.transfer.DataFlowStartMessage;

import java.util.concurrent.ExecutorService;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;

@Consumes({ MediaType.APPLICATION_JSON })
@Produces({ MediaType.APPLICATION_JSON })
@Path(NextCloudHTTPApiController.PATH)
public class NextCloudHTTPApiController implements NextCloudHTTPApi{
    public static final String PATH = "/nextcloudtransfer";
    private NextCloudApi nextCloudApi;
    private final ExecutorService executorService;
    private Monitor monitor;
    private final PipelineService pipelineService;
    private final Vault vault;
    private TypeManager typeManager;
    private TransferProcessStore transferProcessStore;

    public NextCloudHTTPApiController(NextCloudApi nextCloudApi, ExecutorService executorService, Monitor monitor,
                                      PipelineService pipelineService, TypeManager typeManager, Vault vault,
                                      TransferProcessStore transferProcessStore){
        this.nextCloudApi = nextCloudApi;
        this.executorService = executorService;
        this.monitor = monitor;
        this.pipelineService = pipelineService;
        this.typeManager = typeManager;
        this.vault = vault;
        this.transferProcessStore = transferProcessStore;
    }

    @POST
    @Override
    public ResponseEntity<String> startTransferProcess(@RequestBody HttpParts httpParts) {
        var secret = httpParts.getUrl();
        vault.storeSecret(httpParts.getDataRequest().getKeyName(), typeManager.writeValueAsString(secret));


        StoreResult<TransferProcess> transferProcess = transferProcessStore.findByCorrelationIdAndLease(httpParts.getProcessId());
        if(!transferProcess.failed()) {
            transferProcess.getContent().transitionStarted();
            this.update(transferProcess.getContent());


        }

        var dataflow=  DataFlowStartMessage.Builder.newInstance().processId(httpParts.getProcessId())
                .sourceDataAddress(httpParts.getDataAddress())
                .destinationDataAddress(httpParts.getDataRequest())
                .build();


        pipelineService.transfer(dataflow).whenComplete((result, throwable) -> {
            if (result.succeeded()) {
                monitor.info("Transfer completed");
                transferProcess.getContent().transitionCompleted();
                this.update(transferProcess.getContent());

            } else if(result.failed()){
                monitor.severe( result.getFailureMessages().get(0));
                transferProcess.getContent().transitionTerminating( result.getFailureMessages().get(0));
                this.update(transferProcess.getContent());
            }
        });


        return new ResponseEntity<>("", HttpStatus.OK);
    }
    private void update(TransferProcess transferProcess) {
        this.transferProcessStore.save(transferProcess);
        this.monitor.debug(String.format("TransferProcess %s is now in state %s", transferProcess.getId(), TransferProcessStates.from(transferProcess.getState())), new Throwable[0]);
    }
}
