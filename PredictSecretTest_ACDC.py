import os
import sys
import logging
import argparse
import random
import numpy as np
import torch
from torch.utils.data import DataLoader
import torch.backends.cudnn as cudnn
from tqdm import tqdm

from utils.utils import predict_single_volume
from utils.dataset_ACDC import ACDCdataset, RandomGenerator
from lib.networks import MaxViT, MaxViT4Out, MaxViT_CASCADE, MERIT_Parallel, MERIT_Cascaded
import time
    
def acdc_predict(args, model, testloader, test_save_path=None):
    logging.info("{} test iterations per epoch".format(len(testloader)))
    model.eval()
    metric_list = 0.0
    z_spacing_dict = np.load(args.list_dir+'/z_spacing_secrettest.npz')
    print(z_spacing_dict)
    with torch.no_grad():
        for i_batch, sampled_batch in tqdm(enumerate(testloader)):
            h, w = sampled_batch["image"].size()[2:]
            image,case_name = sampled_batch["image"], sampled_batch['case_name'][0]
            
            z_spacing = z_spacing_dict[case_name]
            # print(z_spacing[2])
            
            spacing = (z_spacing[0],z_spacing[1], z_spacing[2])
            metric_i = predict_single_volume(image, model, classes=args.num_classes, patch_size=[args.img_size, args.img_size],test_save_path=test_save_path, case=case_name, z_spacing=spacing)
        print(message)

        
if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--batch_size", default=2, help="batch size") #12
    parser.add_argument("--lr", default=0.0001, help="learning rate")
    parser.add_argument("--max_epochs", default=25)
    parser.add_argument("--img_size", default=256)
    parser.add_argument("--save_path", default="./model_pth/ACDC")
    parser.add_argument("--n_gpu", default=1)
    parser.add_argument("--checkpoint", default=None)
    parser.add_argument("--list_dir", default="./DataProcessed/lists_ACDC") #change the paths here for the secret set...
    parser.add_argument("--root_dir", default="./DataProcessed/") 
    parser.add_argument("--volume_path", default="./DataProcessed/secret")#change the path here for secret set...
    parser.add_argument("--z_spacing", default=10)
    parser.add_argument("--num_classes", default=4)
    parser.add_argument('--test_save_dir', default='./predictions', help='saving prediction as nii!')
    parser.add_argument('--deterministic', type=int,  default=1,
                    help='whether use deterministic training')
    parser.add_argument('--seed', type=int,
                    default=2222, help='random seed')
                
    args = parser.parse_args()
    
    

    if not args.deterministic:
        cudnn.benchmark = True
        cudnn.deterministic = False
    else:
        cudnn.benchmark = False
        cudnn.deterministic = True
    
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed(args.seed)

    # config_vit.n_classes = args.num_classes
    # config_vit.n_skip = args.n_skip

    args.is_pretrain = True
    args.exp = 'MERIT_Cascaded_Small_loss_MUTATION_w3_7_' + str(args.img_size)
    

    net = MERIT_Cascaded(n_class=args.num_classes, img_size_s1=(args.img_size,args.img_size), img_size_s2=(224,224), model_scale='small', decoder_aggregation='additive', interpolation='bilinear').cuda()

    # snapshot = os.path.join(snapshot_path, 'best.pth')
    snapshot = "./model_pth/ACDC/MERIT_Cascaded_Small_loss_MUTATION_w3_7_256/MERIT_Cascaded_Small_loss_MUTATION_w3_7_pretrain_epo25_bs8_lr0.0001_256_s2222_run144621/epoch=24_lr=0.0001_avg_dcs=0.877204939735222.pth" ## change the path of the model trained here...
   
    # if not os.path.exists(snapshot): snapshot = snapshot.replace('best', 'epoch_'+str(args.max_epochs-1))
    net.load_state_dict(torch.load(snapshot))
    snapshot_name = snapshot.split('/')[-2]

    log_folder = 'test_log/test_log_' + args.exp
    os.makedirs(log_folder, exist_ok=True)
    logging.basicConfig(filename=log_folder + '/'+snapshot_name+".txt", level=logging.INFO, format='[%(asctime)s.%(msecs)03d] %(message)s', datefmt='%H:%M:%S')
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
    logging.info(str(args))
    logging.info(snapshot_name)

    # args.test_save_dir = os.path.join(snapshot_path, args.test_save_dir)
    # test_save_path = os.path.join(args.test_save_dir, args.exp, snapshot_name)
    # os.makedirs(test_save_path, exist_ok=True)
    
    
    db_test =ACDCdataset(base_dir=args.volume_path,list_dir=args.list_dir, split="secrettest") #loads the data and saves them as {image: ..}
    testloader = DataLoader(db_test, batch_size=1, shuffle=False)
    
    test_save_path = './SecretTestResults_new' ## change the saving path here.
    test_save_path = os.path.join(test_save_path, snapshot_name)
    os.makedirs(test_save_path, exist_ok=True)
    
    acdc_predict(args, net, testloader, test_save_path)


