package com.ionos.edc.dataplane;

import com.ionos.edc.dataplane.http.NextCloudHTTPApiController;
import com.ionos.edc.nextcloudapi.NextCloudApi;
import org.eclipse.edc.connector.controlplane.transfer.spi.store.TransferProcessStore;
import org.eclipse.edc.connector.dataplane.spi.pipeline.DataTransferExecutorServiceContainer;
import org.eclipse.edc.connector.dataplane.spi.pipeline.PipelineService;
import org.eclipse.edc.http.spi.EdcHttpClient;
import org.eclipse.edc.runtime.metamodel.annotation.Extension;
import org.eclipse.edc.runtime.metamodel.annotation.Inject;
import org.eclipse.edc.runtime.metamodel.annotation.SettingContext;
import org.eclipse.edc.spi.security.Vault;
import org.eclipse.edc.spi.system.ServiceExtension;
import org.eclipse.edc.spi.system.ServiceExtensionContext;
import org.eclipse.edc.spi.types.TypeManager;
import org.eclipse.edc.web.spi.WebService;
import org.eclipse.edc.web.spi.configuration.ApiContext;
import org.eclipse.edc.web.spi.configuration.WebServiceConfigurer;
import org.eclipse.edc.web.spi.configuration.WebServiceSettings;


@Extension(value = DataPlaneNextcloud.NAME)
public class DataPlaneNextcloud  implements ServiceExtension {
    public static final String NAME = "Data Plane NextCloud";
    @Inject
    private WebService webService;
    @Inject
    private PipelineService pipelineService;
    @Inject
    private DataTransferExecutorServiceContainer executorContainer;
    @Inject
    private Vault vault;
    @Inject
    private TypeManager typeManager;
    @Inject
    private NextCloudApi nextCloudApi;
    @Inject
    private EdcHttpClient httpClient;

    @Inject
    private TransferProcessStore transferProcessStore;



    @Override
    public String name() {
        return NAME;
    }

    @Override
    public void initialize(ServiceExtensionContext context) {


        var monitor = context.getMonitor();

        var sourceFactory = new  NextCloudDataSourceFactory(nextCloudApi, typeManager, vault);
        pipelineService.registerFactory(sourceFactory);

        var sinkFactory = new NextCloudDataSinkFactory(executorContainer.getExecutorService(), monitor, vault,
                typeManager, nextCloudApi);


        pipelineService.registerFactory(sinkFactory);
        NextCloudHTTPApiController nextApi =  new NextCloudHTTPApiController(nextCloudApi,executorContainer.getExecutorService(),
                monitor,pipelineService, typeManager, vault, transferProcessStore);
        webService.registerResource(ApiContext.MANAGEMENT, nextApi);
        context.getMonitor().info(NAME+ " Extension initialized!");
    }
}