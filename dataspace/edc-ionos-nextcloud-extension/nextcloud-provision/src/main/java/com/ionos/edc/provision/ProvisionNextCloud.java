package com.ionos.edc.provision;

import com.ionos.edc.nextcloudapi.NextCloudApi;
import com.ionos.edc.token.NextCloudToken;
import dev.failsafe.RetryPolicy;
import org.eclipse.edc.connector.controlplane.services.spi.transferprocess.TransferProcessService;
import org.eclipse.edc.connector.controlplane.transfer.spi.provision.ProvisionManager;
import org.eclipse.edc.connector.controlplane.transfer.spi.provision.ResourceManifestGenerator;
import org.eclipse.edc.connector.controlplane.transfer.spi.types.TransferProcess;
import org.eclipse.edc.runtime.metamodel.annotation.Extension;
import org.eclipse.edc.runtime.metamodel.annotation.Inject;
import org.eclipse.edc.runtime.metamodel.annotation.Setting;
import org.eclipse.edc.http.spi.EdcHttpClient;
import org.eclipse.edc.spi.monitor.Monitor;
import org.eclipse.edc.spi.security.Vault;
import org.eclipse.edc.spi.system.ServiceExtension;
import org.eclipse.edc.spi.system.ServiceExtensionContext;
import org.eclipse.edc.spi.types.TypeManager;


@Extension(value = ProvisionNextCloud.NAME)
public class ProvisionNextCloud implements ServiceExtension {

    public static final String NAME = "NextCloud Provision";

    @Inject
    private Vault vault;
    @Inject
    private Monitor monitor;
    @Inject
    private TypeManager typeManager;
    @Inject
    private NextCloudApi nextCloudApi;
    @Inject
    private EdcHttpClient httpClient;
    @Inject
    private TransferProcessService transferProcessService;
    @Setting
    private static final String HTTP_RECEIVER_AUTH_KEY = "edc.api.auth.key";

    @Override
    public String name() {
        return NAME;
    }
    
    @Override
    public void initialize(ServiceExtensionContext context) {
        // TODO Auto-generated method stub
        monitor = context.getMonitor();
        monitor.debug("NextCloudProvisionExtension" + "provisionManager");
        var provisionManager = context.getService(ProvisionManager.class);
        monitor.debug("NextCloudProvisionExtension" + "retryPolicy");
        var retryPolicy = (RetryPolicy<Object>) context.getService(RetryPolicy.class);
        monitor.debug("NextCloudProvisionExtension");
        var authKey = context.getSetting(HTTP_RECEIVER_AUTH_KEY, null);
        var nextCloudProvisioner = new NextCloudProvisioner(retryPolicy, monitor, nextCloudApi, httpClient,typeManager.getMapper(), authKey, transferProcessService);

        provisionManager.register(nextCloudProvisioner);

        // register the generator
        monitor.debug("NextCloudProvisionExtension" + "manifestGenerator");
        var manifestGenerator = context.getService(ResourceManifestGenerator.class);
        manifestGenerator.registerGenerator(new NextCloudProviderResourceDefinitionGenerator());
        registerTypes(typeManager);
    }

    @Override
    public void shutdown() {
        ServiceExtension.super.shutdown();
    }

    private void registerTypes(TypeManager typeManager) {
        typeManager.registerTypes(NextCloudProvisionedResource.class, NextCloudResourceDefinition.class, NextCloudToken.class);
    }
}