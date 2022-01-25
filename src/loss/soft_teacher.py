import torch
from torch.nn.functional import softmax, cross_entropy


def soft_teacher_classification_loss(
        class_logits: torch.Tensor,
        labels: torch.Tensor,
        teacher_background_scores: torch.Tensor,
        is_pseudo: torch.Tensor,
        unsupervised_loss_weight: float = 1.0,
        student_unsupervised_foreground_threshold: float = 0.9
) -> torch.Tensor:
    epsilon = 10e-5
    class_probabilities = softmax(class_logits, -1)
    values, indices = torch.max(class_probabilities, -1)
    select_supervised_foreground = indices > 0
    select_unsupervised_foreground = torch.logical_and(indices > 0, values > student_unsupervised_foreground_threshold)

    unweighted_loss = cross_entropy(class_logits, labels, reduction='none')

    select_supervised_background = torch.logical_and(torch.logical_not(select_supervised_foreground), torch.logical_not(is_pseudo))
    select_unsupervised_background = torch.logical_and(torch.logical_not(select_unsupervised_foreground), is_pseudo)
    reliability_weight = teacher_background_scores[select_unsupervised_background] \
                         / (torch.sum(teacher_background_scores[select_unsupervised_background]) + epsilon)
    device = unweighted_loss.device
    if torch.numel(unweighted_loss[select_supervised_background]) > 0:
        supervised_background_loss = torch.mean(unweighted_loss[select_supervised_background])
    else:
        supervised_background_loss = torch.tensor(0., device=device)
    if torch.numel(unweighted_loss[select_unsupervised_background]) > 0:
        unsupervised_background_loss = torch.mean(reliability_weight * unweighted_loss[select_unsupervised_background])
    else:
        unsupervised_background_loss = torch.tensor(0., device=device)

    select_supervised_foreground = torch.logical_and(select_supervised_foreground, torch.logical_not(is_pseudo))
    select_unsupervised_foreground = torch.logical_and(select_unsupervised_foreground, is_pseudo)
    if torch.numel(unweighted_loss[select_supervised_foreground]) > 0:
        supervised_foreground_loss = torch.mean(unweighted_loss[select_supervised_foreground])
    else:
        supervised_foreground_loss = torch.tensor(0., device=device)
    if torch.numel(unweighted_loss[select_unsupervised_foreground]) > 0:
        unsupervised_foreground_loss = torch.mean(unweighted_loss[select_unsupervised_foreground])
    else:
        unsupervised_foreground_loss = torch.tensor(0., device=device)

    # TODO: Maybe divide by 4 to not destroy equilibrium between classification and regression loss (own addition)
    supervised_loss = supervised_foreground_loss + supervised_background_loss
    unsupervised_loss = unsupervised_foreground_loss + unsupervised_background_loss
    # TODO: Maybe additional hyperparameter to weight unsupervised loss?
    return supervised_loss + unsupervised_loss_weight * unsupervised_loss