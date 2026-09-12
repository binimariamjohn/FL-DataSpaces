package com.ionos.edc.dataplane;

import com.ionos.edc.dataplane.validation.NextCloudDataDestinationValidator;
import com.ionos.edc.nextcloudapi.NextCloudApi;
import com.ionos.edc.schema.NextcloudSchema;
import com.ionos.edc.token.NextCloudToken;
import org.eclipse.edc.connector.dataplane.spi.pipeline.DataSink;
import org.eclipse.edc.connector.dataplane.spi.pipeline.DataSinkFactory;
import org.eclipse.edc.spi.types.domain.DataAddress;
import org.eclipse.edc.spi.types.domain.transfer.DataFlowStartMessage;
import org.eclipse.edc.validator.spi.Validator;
import org.eclipse.edc.spi.EdcException;
import org.eclipse.edc.spi.monitor.Monitor;
import org.eclipse.edc.spi.result.Result;
import org.eclipse.edc.spi.security.Vault;
import org.eclipse.edc.spi.types.TypeManager;
import org.jetbrains.annotations.NotNull;
import java.util.concurrent.ExecutorService;

public class NextCloudDataSinkFactory  implements DataSinkFactory {

    private final Validator<DataAddress> validation = new NextCloudDataDestinationValidator();
    private final ExecutorService executorService;
    private final Monitor monitor;
    private Vault vault;
    private TypeManager typeManager;
    private NextCloudApi nextCloudApi;


    public NextCloudDataSinkFactory(@NotNull ExecutorService executorService, Monitor monitor,
                                    Vault vault, TypeManager typeManager, NextCloudApi nextCloudApi ) {
        this.executorService = executorService;
        this.monitor = monitor;
        this.vault = vault;
        this.typeManager = typeManager;
        this.nextCloudApi = nextCloudApi;

    }

    @Override
    public String supportedType() {
        return NextcloudSchema.TYPE;
    }

    @Override
    public boolean canHandle(DataFlowStartMessage request) {
        
        return NextcloudSchema.TYPE.equals(request.getDestinationDataAddress().getType());
    }

    @Override
    public @NotNull Result<Void> validateRequest(DataFlowStartMessage request) {
        var destination = request.getDestinationDataAddress();

        return validation.validate(destination).toResult();
    }

    @Override
    public DataSink createSink(DataFlowStartMessage request) {
        var validationResult = validateRequest(request);
        if (validationResult.failed()) {
            throw new EdcException(String.join(", ", validationResult.getFailureMessages()));
        }

        var destination = request.getDestinationDataAddress();;
        var secret = vault.resolveSecret(destination.getKeyName());
        if (secret != null) {
            var token = typeManager.readValue(secret, NextCloudToken.class);

            return NextCloudDataSink.Builder.newInstance()

                        .filePath(destination.getStringProperty(NextcloudSchema.FILE_PATH))
                        .fileName(request.getSourceDataAddress().getStringProperty(NextcloudSchema.FILE_NAME))
                        .downloadable(token.getDownloadable())
                        .requestId(request.getProcessId()).executorService(executorService)
                        .monitor(monitor).nextCloudApi(nextCloudApi).build();

        } else {
            return NextCloudDataSink.Builder.newInstance()
                    .filePath(destination.getStringProperty(NextcloudSchema.FILE_PATH))
                    .fileName(request.getSourceDataAddress().getStringProperty(NextcloudSchema.FILE_NAME))
                    .requestId(request.getId()).executorService(executorService)
                    .monitor(monitor).nextCloudApi(nextCloudApi).build();
        }
    }



}
